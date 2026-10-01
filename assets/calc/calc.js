/* The damage calculator, calc.html.
 *
 * build_calc.py has already read every card's text into effects, so this file
 * only does arithmetic and keeps the form in step with it. Nothing here knows
 * a card by name except through pool.json; a new card's wording is taught to
 * the builder, never to this file.
 *
 * Two kinds of attack, and the difference is the whole deck:
 *
 *   counters  Chaotic Pain places 13 damage counters. Weakness, Resistance,
 *             "takes less damage", and damage prevention all miss it. Only
 *             effect prevention stops it: Mist Energy, Hide 'n' Sneak, a
 *             Battle Cage over the Bench.
 *   damage    everything else. Active Spot only. Base, then the changes
 *             "before Weakness", then Weakness and Resistance, then the
 *             changes "after", then anything that prevents it outright.
 *
 * Effects carry condition tokens like "atk:ex" or "tgt:bench"; test() is
 * where each one is read. The builder's docstring lists where they come from.
 *
 * Android notes, since that is where this runs. The search listens to input
 * and never to keydown codes, which Gboard reports as 229 while composing.
 * The list closes on a tap outside it, not on blur: closing on blur is the
 * classic bug where the tap that picks a suggestion lands after the list has
 * already gone.
 */
// @ts-check
"use strict";

/** @type {any} */
let pool = null;
/** @type {any} the picked Pokémon */
let card = null;

const BLANK = {
	id: "",
	basic: 0,
	specials: /** @type {string[]} */ ([]),
	position: "active",
	damage: 0,
	tool: "",
	last: "",
};

/* the whole form. stadium, attacker, and the dog's Poison are not about the
   opponent's Pokémon, so Clear leaves them alone. */
const state = {
	...structuredClone(BLANK),
	stadium: "",
	attacker: "gengar",
	poisoned: true,
};

const SAVE = "calc";
const $ = (/** @type {string} */ s) => /** @type {any} */ (document.querySelector(s));

const section = $("[data-opponent]");
const search = $("[data-search]");
const input = $("#q");
const hits = $("#hits");
const clear = $("[data-clear]");
const art = $("[data-art]");
/* the picture the page starts with, so the builder names the file once */
const CARD_BACK = art.querySelector("img").getAttribute("src");
const caption = $("[data-preview] figcaption");
const lastField = $("[data-last]");
const lastSelect = $("#last");
const chips = $("[data-chips]");
const callouts = $("[data-callouts]");
const moves = $("[data-moves] tbody");
const notes = $("[data-notes]");

/* --- small helpers ------------------------------------------------------ */

function esc(/** @type {any} */ s) {
	return String(s ?? "").replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
}

/* letters and digits only, accents folded, so "flabebe" finds Flabébé and
   "mega luc" finds Mega Lucario ex. the same folding as collection.js. */
function plain(/** @type {string} */ s) {
	return (s || "")
		.normalize("NFD")
		.replace(/[̀-ͯ]/g, "")
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, "");
}

function fuzzy(/** @type {string} */ q, /** @type {string} */ name) {
	let i = 0;
	for (const ch of name) {
		if (ch === q[i]) i++;
		if (i === q.length) return true;
	}
	return false;
}

function typeIcon(/** @type {string} */ t) {
	return `<img src="./assets/types/${t.toLowerCase()}.png" alt="${esc(t)}" />`;
}

/* card text in a callout: *italics* and [C] the way the deck pages write them */
function fmt(/** @type {string} */ s) {
	return esc(s)
		.replace(/\*([^*]+)\*/g, "<em>$1</em>")
		.replace(/\[C\]/g, typeIcon("Colorless"));
}

function list(/** @type {string[]} */ names) {
	if (names.length < 3) return names.join(" and ");
	return `${names.slice(0, -1).join(", ")}, and ${names.at(-1)}`;
}

function image(/** @type {string} */ id, /** @type {string} */ size) {
	return `https://images.scrydex.com/pokemon/${encodeURIComponent(id)}/${size}`;
}

/* --- the engine --------------------------------------------------------- */

function named(/** @type {string} */ name) {
	return pool.named[name] || { fx: [] };
}

function stadiumFx() {
	return state.stadium ? named(state.stadium).fx : [];
}

/* every effect on the table right now, each tagged with where it came from */
function effects() {
	if (!card) return [];
	const out = [];
	const stadium = stadiumFx();
	// Team Rocket's Watchtower: Colorless Pokémon have no Abilities
	const silenced = stadium.some((/** @type {any} */ f) => f.k === "noAbilities")
		&& card.types.includes("Colorless");
	if (!silenced) {
		for (const a of card.abilities || []) {
			for (const f of a.fx || []) out.push({ ...f, src: a.name });
		}
	}
	const last = (card.next || []).find((/** @type {any} */ m) => m.name === state.last);
	if (last) {
		for (const f of last.fx) out.push({ ...f, src: `${last.name} (last turn)` });
	}
	const noTools = stadium.some((/** @type {any} */ f) => f.k === "noTools");
	if (state.tool && !noTools) {
		for (const f of named(state.tool).fx) out.push({ ...f, src: state.tool });
	}
	for (const e of state.specials) {
		for (const f of named(e).fx) out.push({ ...f, src: e });
	}
	for (const f of stadium) out.push({ ...f, src: state.stadium });
	return out;
}

function hasAbility(/** @type {string} */ name) {
	return (card?.abilities || []).some((/** @type {any} */ a) => a.name === name);
}

/* whether this attacker counts as "a Pokémon that has an Ability" right now.
   three cards take that away: Watchtower from a Colorless one, an Active Iron
   Thorns ex from any Pokémon ex, an Active Flutter Mane from your Active. */
function attackerAbility(/** @type {any} */ atk) {
	if (!atk.ability) return false;
	const watch = stadiumFx().some((/** @type {any} */ f) => f.k === "noAbilities");
	if (watch && atk.type === "Colorless") return false;
	if (state.position === "active") {
		if (atk.ex && hasAbility("Initialization")) return false;
		if (hasAbility("Midnight Fluttering")) return false;
	}
	return true;
}

/* one condition token. an unknown one is false, so a token the builder
   learns before this file does switches its effect off rather than on. */
function test(/** @type {string} */ tok, /** @type {any} */ c) {
	const [side, rest] = tok.split(/:(.*)/s);
	if (side === "dmg") {
		if (c.dmg === undefined) return false;
		const m = /^(>=|<=)(\d+)$/.exec(rest);
		if (!m) return false;
		return m[1] === ">=" ? c.dmg >= +m[2] : c.dmg <= +m[2];
	}
	const neg = rest.startsWith("!");
	const [what, arg] = (neg ? rest.slice(1) : rest).split("=");
	let v = false;
	if (side === "atk") {
		const a = c.atk;
		v = {
			ex: a.ex,
			mega: a.mega,
			basic: a.stage === "Basic",
			evolution: a.stage !== "Basic",
			ability: attackerAbility(a),
			colorless: a.type === "Colorless",
			type: arg?.split("|").includes(a.type),
		}[what] ?? false;   // tera, burned, ancient, future: never this deck
	} else if (side === "tgt") {
		const t = card;
		v = {
			active: state.position === "active",
			bench: state.position === "bench",
			energy: state.basic + state.specials.length > 0,
			special: state.specials.length > 0,
			type: arg?.split("|").some((/** @type {string} */ x) => t.types.includes(x)),
			owner: t.owner === arg,
			stage: t.stage === arg,
			basic: t.stage === "Basic",
			mega: t.tags.includes("mega"),
			rulebox: t.tags.includes("ex"),
			ancient: t.tags.includes("ancient"),
			name: t.name === arg,
		}[what] ?? false;
	}
	return neg ? !v : v;
}

function poisoned() {
	return state.poisoned && !stadiumFx().some((/** @type {any} */ f) => f.k === "noPoison");
}

function counted(/** @type {number} */ n) {
	return n === 1 ? "1 damage counter" : `${n} damage counters`;
}

/* what one attacker does to the picked Pokémon. defending asks the other
   question: what if this attacker was the one their last attack hit. */
function strike(/** @type {any} */ atk, defending = false) {
	const c = { atk, dmg: /** @type {number|undefined} */ (undefined) };
	const all = effects();
	const on = (/** @type {any} */ f) => (defending || !f.defending)
		&& (f.if || []).every((/** @type {string} */ t) => test(t, c));
	const res = {
		dmg: 0, steps: /** @type {string[]} */ ([]), notes: /** @type {any[]} */ ([]),
		blocked: "", reach: true, ko: false, left: 0, hp: 0, prizes: 0,
		cost: 0, cantAttack: "",
	};

	res.cost = all.filter((f) => f.k === "cost" && on(f))
		.reduce((s, f) => s + f.n, 0);
	const stop = all.find((f) => f.k === "cantAttack" && on(f));
	if (stop) res.cantAttack = stop.src;

	if (!card) {
		res.dmg = atk.counters ? atk.counters * 10 : atk.damage
			+ (atk.poison && poisoned() ? atk.poison : 0);
		return res;
	}
	res.hp = card.hp + all.filter((f) => f.k === "hp" && on(f))
		.reduce((s, f) => s + f.n, 0);
	res.prizes = card.prizes;

	if (atk.counters) {
		const block = all.find((f) => f.k === "prevent" && f.what !== "damage" && on(f));
		if (block) {
			res.blocked = block.src;
			return res;
		}
		res.dmg = atk.counters * 10;
		res.steps.push(`${counted(atk.counters)}, no Weakness`);
	} else {
		if (state.position === "bench") {
			res.reach = false;
			return res;
		}
		let d = atk.damage;
		res.steps.push(String(d));
		if (atk.poison && poisoned()) {
			d += atk.poison;
			res.steps.push(`+${atk.poison} Poisoned`);
		}
		for (const f of all) {
			if (f.k === "debuff" && on(f)) {
				d -= f.n;
				res.steps.push(`−${f.n} ${f.src}`);
			}
		}
		d = Math.max(0, d);
		if ((card.weak || []).includes(atk.type)
			&& !all.some((f) => f.k === "noWeak" && on(f))) {
			d *= 2;
			res.steps.push("×2 Weakness");
		}
		const r = (card.resist || []).find((/** @type {any} */ x) => x[0] === atk.type);
		if (r) {
			d -= r[1];
			res.steps.push(`−${r[1]} Resistance`);
		}
		for (const f of all) {
			if (f.k === "reduce" && on(f)) {
				d -= f.n;
				res.steps.push(`−${f.n} ${f.src}`);
			}
			if (f.k === "more" && on(f)) {
				d += f.n;
				res.steps.push(`+${f.n} ${f.src}`);
			}
		}
		d = Math.max(0, d);
		c.dmg = d;
		const block = all.find((f) => f.k === "prevent" && f.what !== "effects" && on(f));
		if (block) {
			res.blocked = block.src;
			return res;
		}
		res.dmg = d;
		for (const f of all) {
			if (f.k === "coin" && on(f)) res.notes.push({ tone: "bad", html: `<b>${esc(f.src)}</b>: a coin flip, and heads stops it.` });
		}
	}

	res.left = res.hp - state.damage - res.dmg;
	res.ko = res.left <= 0;
	if (res.ko && !atk.counters && state.damage === 0
		&& all.some((f) => f.k === "survive" && on(f))) {
		res.ko = false;
		res.left = 10;
		res.notes.push({ tone: "bad", html: "<b>Survival Brace</b> leaves it at 10 HP, then goes to the discard pile." });
	}
	if (res.ko && !atk.counters) {
		res.prizes += all.filter((f) => f.k === "prize" && on(f))
			.reduce((s, f) => s + f.n, 0);
	}
	if (!atk.counters && res.dmg > 0) {
		for (const f of all) {
			if (f.k !== "retaliate" || !on(f)) continue;
			const n = f.n === "equal" ? res.dmg / 10 : f.n;
			res.notes.push({ tone: "bad", html: `<b>${esc(f.src)}</b> puts ${counted(n)} on ${esc(atk.name)}.` });
		}
	}
	return res;
}

/* --- callouts ----------------------------------------------------------- */

/* whether an attacker's hit actually lands on the picked Pokémon */
function lands(/** @type {any} */ r) {
	return !r.blocked && r.reach && !r.cantAttack;
}

function move(/** @type {any} */ a) {
	return `<em>${esc(a.move)}</em>`;
}

/* one line per effect, saying what it does to these five attackers rather
   than repeating the card. an effect that touches none of them says nothing.

   every line is about this effect alone and says nothing about what else
   gets through: with Mist Energy on a Crustle, Rock Inn's "Pain still
   lands" and Mist's "damage still gets through" were each true of their
   own card and both false of the board. what gets through is one summary
   line, worked out from every attacker's actual result. */
function describe(/** @type {any} */ f, /** @type {Map<string, any>} */ results, /** @type {boolean} */ painLands) {
	const A = pool.attackers;
	const b = `<b>${esc(f.src)}</b>`;
	const by = (/** @type {(r: any, a: any) => boolean} */ pick) => A
		.filter((/** @type {any} */ a) => pick(results.get(a.key), a));
	const c = { atk: A[0], dmg: undefined };
	const on = (/** @type {any} */ x) => (x.if || []).every((/** @type {string} */ t) => test(t, c));
	const hitters = A.filter((/** @type {any} */ a) => !a.counters).length;
	switch (f.k) {
	case "prevent": {
		const stopped = by((r) => r.blocked === f.src);
		return stopped.length ? { tone: "bad", html: `${b} stops ${list(stopped.map(move))}.` } : null;
	}
	case "reduce": {
		const hit = by((r) => r.steps.includes(`−${f.n} ${f.src}`));
		if (!hit.length) return null;
		return { tone: "bad", html: `${b}: ${f.n} less damage from ${hit.length === hitters ? "every attack" : list(hit.map(move))}.` };
	}
	case "more":
		return { tone: "good", html: `${b}: ${f.n} more damage from every attack.` };
	case "debuff":
		if (f.defending) return { tone: "bad", html: `${b}: whichever of yours it hit does ${f.n} less until it leaves the Active Spot.` };
		return on(f) ? { tone: "bad", html: `${b}: your attacks do ${f.n} less to it.` } : null;
	case "hp":
		if (!on(f)) return null;
		return f.n > 0
			? { tone: "bad", html: `${b}: ${f.n} more HP, ${results.get(A[0].key).hp} in all.` }
			: { tone: "good", html: `${b}: ${-f.n} less HP, ${results.get(A[0].key).hp} in all.` };
	case "retaliate": {
		// who actually sets it off, which for Tremendous Bomb is one attacker
		// on one kind of target and for Spiky Energy is all four that hit
		const set = by((r) => r.notes.some((/** @type {any} */ n) => n.html.startsWith(`<b>${esc(f.src)}</b> puts`)));
		if (!set.length) return null;
		const who = set.length === hitters ? "whatever damages it" : esc(list(set.map((/** @type {any} */ a) => a.name)));
		return { tone: "bad", html: f.n === "equal"
			? `${b}: ${who} takes as many damage counters as the damage it did.`
			: `${b}: ${counted(f.n)} on ${who}.` };
	}
	case "noWeak":
		return card.weak ? { tone: "bad", html: `${b}: no Weakness this turn.` } : null;
	case "cantAttack": {
		const who = (f.if || []).includes("atk:basic") ? "if it was a Basic, the one it hit" : "the one it hit";
		return { tone: "bad", html: `${b}: ${who} can't attack until it leaves the Active Spot.` };
	}
	case "cost": {
		if (f.defending) return { tone: "bad", html: `${b}: the one it hit pays ${typeIcon("Colorless")} more to attack.` };
		const pays = by((r) => r.cost > 0).map((/** @type {any} */ a) => a.name);
		return pays.length ? { tone: "bad", html: `${b}: ${esc(list(pays))} pays ${typeIcon("Colorless")} more while it is Active.` } : null;
	}
	case "coin":
		return { tone: "bad", html: `${b}: ${fmt(f.text)}` };
	case "survive":
		return { tone: "bad", html: `${b}: from full HP, a Knock Out by damage leaves it at 10 instead.${painLands ? " <em>Chaotic Pain</em> ignores it." : ""}` };
	case "prize":
		return on(f) ? { tone: "bad", html: `${b}: a Knock Out by damage pays 1 Prize less.${painLands ? " A <em>Chaotic Pain</em> Knock Out pays in full." : ""}` } : null;
	case "noPoison":
		return { tone: "bad", html: `${b}: the dog can't be Poisoned, so <em>Chain-Crazed</em> does ${A.find((/** @type {any} */ a) => a.poison)?.damage ?? 130}.` };
	case "noTools":
		return state.tool ? { tone: "good", html: `${b}: their ${esc(state.tool)} does nothing.` } : null;
	case "info":
		return on(f) ? { tone: f.tone, html: `${b}: ${fmt(f.text)}` } : null;
	default:
		return null;
	}
}

function buildCallouts(/** @type {Map<string, any>} */ results) {
	if (!card) return [];
	const A = pool.attackers;
	const pain = A.find((/** @type {any} */ a) => a.counters);
	const painLands = Boolean(pain && lands(results.get(pain.key)));
	const out = [];

	// the answer first: once anything is shut out, what is left. said once,
	// from the results themselves, so no effect speaks for another.
	const through = A.filter((/** @type {any} */ a) => lands(results.get(a.key)));
	if (through.length < A.length) {
		out.push(through.length
			? { tone: "good", html: `<b>Still gets through</b>: ${list(through.map(move))}.` }
			: { tone: "bad", html: "<b>Nothing you have gets through.</b>" });
	}

	for (const f of effects()) {
		const line = describe(f, results, painLands);
		if (line) out.push(line);
	}

	// Weakness only applies in the Active Spot, and only to a hit that lands
	const weakTo = state.position === "active"
		? (card.weak || []).filter((/** @type {string} */ t) => A.some((/** @type {any} */ a) => a.type === t))
		: [];
	const doubled = A.filter((/** @type {any} */ a) => !a.counters && weakTo.includes(a.type)
		&& lands(results.get(a.key)) && results.get(a.key).steps.includes("×2 Weakness"));
	if (doubled.length) {
		out.push({ tone: "good", html: `<b>Weak to ${esc(list(weakTo))}</b>: ${list(doubled.map(move))} double.${painLands ? " <em>Chaotic Pain</em> doesn't." : ""}` });
	}
	const resists = (card.resist || []).filter((/** @type {any} */ r) => A.some((/** @type {any} */ a) => a.type === r[0]));
	for (const [t, n] of resists) out.push({ tone: "bad", html: `<b>Resists ${esc(t)}</b>: ${n} less from your ${esc(t)} attackers.` });

	const hurts = A.filter((/** @type {any} */ a) => card.types.includes(a.weak));
	if (hurts.length) {
		const who = hurts.length === A.length ? "every attacker you have" : list(hurts.map((/** @type {any} */ a) => a.name));
		const types = card.types.filter((/** @type {string} */ t) => hurts.some((/** @type {any} */ a) => a.weak === t));
		const verb = hurts.length === 1 || hurts.length === A.length ? "is" : "are";
		out.push({ tone: "bad", html: `<b>${esc(list(types))}</b>: ${esc(who)} ${verb} weak to it.` });
	}

	if (card.hits) {
		out.push(card.tags.includes("ex")
			? { tone: "good", html: "<b>Pokémon ex</b>: with the Mega in play, <em>Shadowy Concealment</em> takes a Prize off every Knock Out it scores on your Darkness Pokémon." }
			: { tone: "bad", html: "<b>Single-Prize attacker</b>: <em>Shadowy Concealment</em> never applies, so the Mega is 3 Prizes for nothing." });
	}
	if (card.into && !card.tags.includes("ex")) {
		const into = card.into.slice(0, 3);
		const more = card.into.length > 3 ? " and more" : "";
		out.push({ tone: "good", html: `<b>Grows into ${esc(list(into))}</b>${more}.${painLands ? " <em>Chaotic Pain</em> it before it evolves." : ""}` });
	}

	// the hand-written notes say what to do, never what lands or kills: the
	// lines above already know that, and a note can't see a Mist Energy
	const ids = [...(card.notes || [])];
	for (const n of [state.tool, state.stadium, ...state.specials]) {
		if (n) ids.push(...(named(n).notes || []));
	}
	for (const i of new Set(ids)) out.push(pool.notes[i]);

	const seen = new Set();
	return out.filter((l) => !seen.has(l.html) && seen.add(l.html));
}

/* --- search ------------------------------------------------------------- */

let shown = /** @type {any[]} */ ([]);
let active = -1;

function find(/** @type {string} */ q) {
	const p = plain(q);
	if (!p) return [];
	const words = q.split(/\s+/).map(plain).filter(Boolean);
	const scored = [];
	for (const c of pool.cards) {
		let s;
		if (c._key.startsWith(p)) s = 0;
		else if (words.every((w) => c._words.some((/** @type {string} */ x) => x.startsWith(w)))) s = 1;
		else if (c._key.includes(p)) s = 2;
		else if (fuzzy(p, c._key)) s = 3;
		else continue;
		scored.push({ s, c });
	}
	scored.sort((a, b) => a.s - b.s
		|| a.c.name.length - b.c.name.length
		|| a.c.name.localeCompare(b.c.name)
		|| a.c.hp - b.c.hp);
	return scored.slice(0, 10).map((x) => x.c);
}

function showHits() {
	shown = find(input.value);
	active = -1;
	hits.innerHTML = shown.map((c, i) => `<li role="option" id="hit-${i}" data-i="${i}" aria-selected="false">${typeIcon(c.types[0])}<span><b>${esc(c.name)}</b><small>${esc(c.set)} ${esc(c.no)} · ${c.hp} HP</small></span></li>`).join("");
	const open = shown.length > 0;
	hits.hidden = !open;
	input.setAttribute("aria-expanded", String(open));
	input.removeAttribute("aria-activedescendant");
}

function closeHits() {
	hits.hidden = true;
	input.setAttribute("aria-expanded", "false");
	input.removeAttribute("aria-activedescendant");
}

function mark(/** @type {number} */ i) {
	active = i;
	for (const li of hits.children) li.setAttribute("aria-selected", String(+li.dataset.i === i));
	if (i >= 0) {
		input.setAttribute("aria-activedescendant", `hit-${i}`);
		hits.children[i].scrollIntoView({ block: "nearest" });
	}
}

/* a new Pokémon starts clean: what was on the last one isn't on this one */
function choose(/** @type {any} */ c) {
	if (!card || card.id !== c.id) {
		Object.assign(state, structuredClone(BLANK), { position: state.position });
	}
	state.id = c.id;
	card = c;
	input.value = c.name;
	closeHits();
	input.blur();   // drops the phone keyboard
	render();
	// the results sit above the search now, so on a phone bring them back
	// into view once the pick is made
	if (matchMedia("(pointer: coarse)").matches) {
		$("[data-attacker]").scrollIntoView({ block: "start", behavior: "smooth" });
	}
}

input.addEventListener("input", showHits);

input.addEventListener("focus", () => {
	if (card) input.select();
	// on a phone, put the box at the top so the list has room above the
	// keyboard. the banner alone is a third of a Pixel's screen.
	// a quick pick can land before this fires, and then it would drag the
	// page back down past the results the pick just scrolled to
	if (matchMedia("(pointer: coarse)").matches) {
		setTimeout(() => {
			if (document.activeElement === input) search.scrollIntoView({ block: "start", behavior: "smooth" });
		}, 250);
	}
});

/* desktop only, in practice: a phone keyboard sends 229 here while composing,
   and nothing below depends on it */
input.addEventListener("keydown", (/** @type {KeyboardEvent} */ e) => {
	if (hits.hidden && e.key !== "Enter") return;
	if (e.key === "ArrowDown") mark(Math.min(active + 1, shown.length - 1));
	else if (e.key === "ArrowUp") mark(Math.max(active - 1, 0));
	else if (e.key === "Enter") {
		const c = shown[active] || shown[0];
		if (c) choose(c);
	} else if (e.key === "Escape") closeHits();
	else return;
	e.preventDefault();
});

hits.addEventListener("click", (/** @type {MouseEvent} */ e) => {
	const li = /** @type {HTMLElement} */ (e.target).closest("li");
	if (li) choose(shown[+(li.dataset.i ?? -1)]);
});

document.addEventListener("pointerdown", (e) => {
	if (!search.contains(e.target)) closeHits();
});

clear.addEventListener("click", () => {
	Object.assign(state, structuredClone(BLANK));
	card = null;
	input.value = "";
	closeHits();
	render();
});

/* --- the rest of the form ----------------------------------------------- */

document.addEventListener("click", (e) => {
	const btn = /** @type {HTMLElement} */ (e.target).closest("[data-step]");
	if (btn instanceof HTMLElement) {
		const key = /** @type {"basic"|"damage"} */ (btn.dataset.step);
		state[key] = Math.max(0, state[key] + Number(btn.dataset.by));
		render();
		return;
	}
	const chip = /** @type {HTMLElement} */ (e.target).closest("[data-remove]");
	if (chip instanceof HTMLElement) {
		state.specials.splice(Number(chip.dataset.remove), 1);
		render();
	}
});

$("#damage").addEventListener("input", (/** @type {Event} */ e) => {
	const v = parseInt(/** @type {HTMLInputElement} */ (e.target).value, 10);
	state.damage = Number.isFinite(v) && v > 0 ? v : 0;
	render(false);
});

$("#special").addEventListener("change", (/** @type {Event} */ e) => {
	const sel = /** @type {HTMLSelectElement} */ (e.target);
	if (sel.value) state.specials.push(sel.value);
	sel.value = "";
	render();
});

for (const id of ["tool", "stadium", "last"]) {
	$(`#${id}`).addEventListener("change", (/** @type {Event} */ e) => {
		state[/** @type {"tool"|"stadium"|"last"} */ (id)] = /** @type {HTMLSelectElement} */ (e.target).value;
		render();
	});
}

document.addEventListener("change", (e) => {
	const el = /** @type {HTMLInputElement} */ (e.target);
	if (el.name === "position") state.position = el.value;
	else if (el.name === "attacker") state.attacker = el.value;
	else if (el.name === "poisoned") state.poisoned = el.checked;
	else return;
	render();
});

/* --- drawing ------------------------------------------------------------ */

function verdict(/** @type {any} */ r) {
	if (!card) return "";
	if (r.cantAttack) return `<span data-verdict="no">Can't attack: ${esc(r.cantAttack)}</span>`;
	if (r.blocked) return `<span data-verdict="no">Blocked by ${esc(r.blocked)}</span>`;
	if (!r.reach) return `<span data-verdict="no">Active Spot only</span>`;
	if (r.ko) return `<span data-verdict="ok">KO · ${r.prizes} Prize${r.prizes === 1 ? "" : "s"}</span>`;
	return `<span data-verdict="left">${r.left} HP left</span>`;
}

function badge(/** @type {any} */ r) {
	if (r.blocked) return ["✕", "no"];
	if (!r.reach) return ["—", "no"];
	if (!card) return [String(r.dmg), ""];
	return r.ko ? ["KO", "ok"] : [String(r.dmg), ""];
}

/* the three cells for one attacker: attack, cost, damage */
function cells(/** @type {any} */ atk, /** @type {any} */ r) {
	const extra = Array.from({ length: r.cost }, () => typeIcon("Colorless").replace("<img", "<img data-extra"));
	const cost = atk.cost.map(typeIcon).join("") + extra.join("");
	const poison = atk.poison
		? `<label data-poison><input type="checkbox" name="poisoned"${state.poisoned ? " checked" : ""}${poisoned() || !state.poisoned ? "" : " disabled"} /> Poisoned</label>`
		: "";
	const big = r.blocked || !r.reach ? "—" : String(r.dmg);
	const steps = card && !r.blocked && r.reach ? r.steps.join(" ") : "";
	return [
		`<b>${esc(atk.move)}</b>${poison}`,
		cost,
		`<strong>${big}</strong>${steps ? `<small>${esc(steps)}</small>` : ""}${verdict(r)}`,
	];
}

/* every attacker's version of a cell, stacked in one grid cell with only the
   picked one visible. the cell is as tall as the tallest of the five, which
   is the dog with its Poisoned switch, so changing attacker never moves the
   page under your thumb. visibility, not display, is what keeps the hidden
   ones holding their space, and it also keeps them out of the tab order. */
function stack(/** @type {string[]} */ parts, tag = "div") {
	return parts.map((html, i) => {
		const off = pool.attackers[i].key === state.attacker ? "" : " data-off";
		return `<${tag}${off}>${html}</${tag}>`;
	}).join("");
}

/* what changes if this attacker was the one their last attack hit */
function hitLines(/** @type {any} */ atk, /** @type {any} */ r) {
	if (!card || !effects().some((f) => f.defending)) return [];
	const alt = strike(atk, true);
	const src = state.last;
	const out = [];
	if (alt.cantAttack) {
		out.push({ tone: "bad", html: `If ${esc(atk.name)} took <b>${esc(src)}</b>, it can't attack until it leaves the Active Spot.` });
	} else {
		if (alt.dmg !== r.dmg) {
			out.push({ tone: "bad", html: `If ${esc(atk.name)} took <b>${esc(src)}</b>, <em>${esc(atk.move)}</em> does ${alt.dmg}${alt.ko ? ", still a KO" : `, ${alt.left} HP left`}.` });
		}
		if (alt.cost > r.cost) {
			out.push({ tone: "bad", html: `If ${esc(atk.name)} took <b>${esc(src)}</b>, <em>${esc(atk.move)}</em> costs ${typeIcon("Colorless")} more.` });
		}
	}
	return out;
}

function lines(/** @type {any[]} */ items) {
	return items.map((l) => `<li data-tone="${l.tone}">${l.html}</li>`).join("");
}

/* a link out of a callout goes to a new tab, so the calculator and
   everything typed into it is still there to come back to */
function newTab(/** @type {HTMLElement} */ box) {
	for (const a of box.querySelectorAll("a")) {
		a.target = "_blank";
		a.rel = "noopener";
	}
}

function render(syncDamage = true) {
	// the preview, and Clear only once there is something to clear
	clear.hidden = !card;
	const img = art.querySelector("img");
	if (card) {
		art.href = image(card.id, "large");
		if (img.dataset.id !== card.id) {
			img.src = image(card.id, "medium");
			img.alt = card.name;
			img.dataset.id = card.id;
		}
		caption.textContent = `${card.name} · ${card.set} ${card.no}`;
	} else {
		// the card back holds the spot, and links nowhere
		art.removeAttribute("href");
		img.src = CARD_BACK;
		img.alt = "";
		img.dataset.id = "";
		caption.textContent = "Pick a Pokémon";
	}

	$("#basic").textContent = state.basic;
	$("#energy-total").textContent = state.basic + state.specials.length;
	chips.innerHTML = state.specials.map((s, i) => `<li><button type="button" data-remove="${i}">${esc(s)} <b>×</b></button></li>`).join("");
	if (syncDamage) $("#damage").value = state.damage;
	$("#tool").value = state.tool;
	$("#stadium").value = state.stadium;
	for (const el of document.querySelectorAll('[name="position"]')) {
		/** @type {HTMLInputElement} */ (el).checked = /** @type {HTMLInputElement} */ (el).value === state.position;
	}

	const next = card?.next || [];
	lastField.hidden = !next.length;
	lastSelect.innerHTML = '<option value="">Nothing that lasts</option>'
		+ next.map((/** @type {any} */ m) => `<option value="${esc(m.name)}">${esc(m.name)}${m.when ? ` (${esc(m.when)})` : ""}</option>`).join("");
	lastSelect.value = state.last;

	const results = new Map(pool.attackers.map((/** @type {any} */ a) => [a.key, strike(a)]));
	callouts.innerHTML = lines(buildCallouts(results));
	newTab(callouts);

	for (const a of pool.attackers) {
		const out = $(`[data-badge="${a.key}"]`);
		const [text, tone] = badge(results.get(a.key));
		out.textContent = text;
		out.dataset.verdict = tone;
		/** @type {HTMLInputElement} */ ($(`[name="attacker"][value="${a.key}"]`)).checked = a.key === state.attacker;
	}
	const all = pool.attackers.map((/** @type {any} */ a) => cells(a, results.get(a.key)));
	moves.innerHTML = "<tr>" + ["attack", "cost", "damage"].map((col, c) => `<td data-${col}><div data-stack>${stack(all.map((x) => x[c]))}</div></td>`).join("") + "</tr>";
	// the notes under the table stack the same way, so a note that only one
	// attacker gets doesn't push the opponent section down when it appears
	const said = pool.attackers.map((/** @type {any} */ a) => {
		const r = results.get(a.key);
		return lines([...r.notes, ...hitLines(a, r)]);
	});
	notes.innerHTML = said.some(Boolean) ? stack(said, "ul") : "";
	newTab(notes);

	try {
		localStorage.setItem(SAVE, JSON.stringify(state));
	} catch {
		// private window or storage off: the form still works, it just
		// won't survive a reload
	}
}

/* --- start -------------------------------------------------------------- */

async function start() {
	const res = await fetch(section.dataset.pool);
	pool = await res.json();
	for (const c of pool.cards) {
		c._key = plain(c.name);
		c._words = c.name.split(/[\s-]+/).map(plain);
	}
	try {
		const saved = JSON.parse(localStorage.getItem(SAVE) || "null");
		if (saved && typeof saved === "object") {
			for (const k of Object.keys(state)) {
				if (k in saved && typeof saved[k] === typeof state[/** @type {keyof typeof state} */ (k)]) {
					/** @type {any} */ (state)[k] = saved[k];
				}
			}
		}
	} catch {
		// a bad save is no save
	}
	card = pool.cards.find((/** @type {any} */ c) => c.id === state.id) || null;
	if (!card) Object.assign(state, structuredClone(BLANK));
	// a saved Tool or Stadium that rotated out would leave the menu blank
	if (state.tool && !pool.named[state.tool]) state.tool = "";
	if (state.stadium && !pool.named[state.stadium]) state.stadium = "";
	state.specials = state.specials.filter((s) => pool.named[s]);
	input.value = card ? card.name : "";
	render();
}

start().catch((err) => {
	caption.textContent = "The card list didn't load. Reload to try again.";
	console.error(err);
});
