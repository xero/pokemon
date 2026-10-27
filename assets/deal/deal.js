/* The dealt deck list, deal.html.
 *
 * Progressive enhancement over the strip build_deck_html.py writes. Every
 * <figure> keeps its link, its scan, and its count badge; this file wraps
 * the scan in a two-faced card, stacks every card face down on a pile,
 * throws them one at a time to the slot the grid already gave them, and
 * turns them face up in a wave.
 *
 * The grid is never repositioned. The flight is the FLIP trick: each slot
 * is measured where it already is, the card is pushed to the pile with a
 * transform, and animated back to none. So the strip wraps exactly as it
 * did without the script, and the last frame is the page as it was before
 * the script ran. Slots are measured off the figures, which never move,
 * and kept relative to the article, so a measurement survives a scroll and
 * a card in mid-air. Resizing while the pile is waiting re-measures it;
 * resizing mid-air is left alone, since every card lands at "no transform"
 * regardless.
 *
 * The animations are Web Animations, not CSS transitions, because every
 * beat is sequenced off the last one's finished promises and a replay has
 * to be able to cancel the lot. Each animation fills both ways and is
 * cancelled only after the base style has been set to its last frame, so
 * nothing snaps. moveAll() is that pattern once, and the deal, the gather,
 * the collapse, the wash, and the slide are all calls to it.
 *
 * The $$$ in the heading swaps the deck for its pricier prints, the
 * showcase at the foot of the Overgrowth page, without leaving the strip:
 * every card turns face down, the pile rebuilds in the middle, gets
 * shuffled the way deck.of.cards does it, slides to the corner, and the
 * deal runs again with the other art behind the backs. Each scan carries
 * the other print's url in data-bling-src, written by build_deal.py.
 *
 * Nothing starts until the strip scrolls into view, and nothing starts on
 * its own under prefers-reduced-motion. The buttons are an explicit ask,
 * so they play either way.
 */
// @ts-check
"use strict";

/** milliseconds, at normal speed */
const T = {
	hold: 350,        // the pile sits still before the first throw
	flight: 560,      // one card, pile to slot
	stagger: 75,      // between one throw and the next
	settle: 220,      // after the last landing, before the first turn
	flip: 640,        // one card turning over
	flipStagger: 40,  // between turns, in deal order
	ripple: 720,      // the whole wave, pile outward
	fade: 240,        // the count badges, in after the deal and out before
	                  // anything takes the cards away
	gather: 420,      // every card back onto the pile, for a replay
	decode: 1500,     // the most the turn waits for local scans
	remote: 6000,     // the most the swap waits for a print off the network
	collapse: 480,    // the dealt strip onto the pile in the middle
	flick: 420,       // the shuffle: each card out to one side, and back
	step: 10,         // between one card's flick and the next
	slide: 520,       // the stack over to the corner it deals from
};

/** the shuffle's flick: sideways by this share of the card's width. only
 * sideways: fanning the stack open vertically was tried and looked worse */
const FLICK = { min: 0.32, max: 0.97 };

/** how far a card in the pile sits from the one above it, in px */
const PILE = { x: 0.25, y: 0.3 };

/** how far a thrown card lifts toward the viewer at the top of its arc */
const LIFT = 1.1;

const EASE = "cubic-bezier(0.4, 0, 0.2, 1)";

const DEFAULTS = { origin: "top-left", flip: "ripple", speed: "1" };
const KEY = "deal:opts";

/** @typedef {{origin: string, flip: string, speed: string}} Opts */
/** @typedef {{x: number, y: number, w: number, h: number}} Rect */
/** @typedef {{tx: number, ty: number, tilt: number, from: string}} Start */
/**
 * @typedef {object} Move  one card's part in a beat
 * @property {Keyframe[]} frames
 * @property {string} end     the inline transform to leave it with; "" is
 *                            home, and also hands back the figure's z-index
 * @property {number} delay
 * @property {number} duration
 * @property {string} [easing]
 * @property {number} [z]     the figure's z-index from the start of the beat
 * @property {FillMode} [fill]  "both" unless a beat starts while the one
 *                            before it is still finishing, when "forwards"
 *                            keeps it from applying during its delay
 */
/**
 * @typedef {object} Deck
 * @property {HTMLElement} article
 * @property {HTMLElement[]} figs
 * @property {HTMLElement[]} movers
 * @property {HTMLElement[]} cards
 * @property {HTMLImageElement[]} fronts
 * @property {string[]} regular  every front's own scan
 * @property {string[]} bling    the pricier print of the same card, or ""
 * @property {object} token      the run that owns the animations in flight
 * @property {Rect[]} rects      every slot, relative to the article
 * @property {{w: number, h: number}} box  the article
 * @property {{x: number, y: number}} pile the top card's corner, likewise
 * @property {number[]} depth    how far down the pile each card sits: 0 is
 *                               the top, and the first to be dealt
 * @property {number[]} tilt     each card's lean on the pile, in degrees
 * @property {HTMLElement} [button]  the $$$, when the strip has one
 */

/** @type {WeakMap<HTMLElement, Deck>} */
const decks = new WeakMap();

const sleep = (/** @type {number} */ ms) =>
	new Promise(r => setTimeout(r, ms));
const frame = () => new Promise(r => requestAnimationFrame(() => r(0)));
const rand = (/** @type {number} */ a, /** @type {number} */ b) =>
	a + Math.random() * (b - a);
const px = (/** @type {number} */ n) => `${n.toFixed(2)}px`;
const deg = (/** @type {number} */ n) => `${n.toFixed(2)}deg`;

/** 0..n-1 in a random order */
function shuffled(/** @type {number} */ n) {
	const out = Array.from({ length: n }, (_, i) => i);
	for (let i = n - 1; i > 0; i--) {
		const j = Math.floor(Math.random() * (i + 1));
		[out[i], out[j]] = [out[j], out[i]];
	}
	return out;
}

/* ---------------------------------------------------------------------
   the markup */

/**
 * Wrap every scan in the strip in a two-faced card.
 *
 *   <figure>
 *     <a>                             the mover
 *       <span data-card>              the thing that turns
 *         <span data-face="front"><img scan /></span>
 *         <span data-face="back"><img back /></span>
 *     <span data-count />             the badge, flat on the slot
 *
 * The badge moves out of the link and after it, so it sits on the slot
 * rather than on the card: it never flies, never turns, and never tilts,
 * and the stylesheet keeps it invisible until the deal is over. It is
 * ours, not the card's, and that is how it should read. A figure with no
 * link gets a span to move instead.
 *
 * @param {HTMLElement} article
 */
function enhance(article) {
	const back = article.dataset.dealBack;
	if (!back) return null;
	const figs = /** @type {HTMLElement[]} */ ([]);
	const movers = /** @type {HTMLElement[]} */ ([]);
	const cards = /** @type {HTMLElement[]} */ ([]);
	const fronts = /** @type {HTMLImageElement[]} */ ([]);
	for (const fig of article.querySelectorAll("figure")) {
		const img = fig.querySelector("img");
		if (!img || fig.querySelector("[data-card]")) continue;
		let mover = img.parentElement;
		if (!mover || mover === fig) {
			mover = document.createElement("span");
			fig.append(mover);
		}
		mover.dataset.mover = "";
		const count = fig.querySelector("[data-count]");
		const card = document.createElement("span");
		card.dataset.card = "";
		const front = document.createElement("span");
		front.dataset.face = "front";
		const rear = document.createElement("span");
		rear.dataset.face = "back";
		const b = document.createElement("img");
		b.src = back;
		b.alt = "";
		b.width = 365;
		b.height = 512;
		b.decoding = "async";
		front.append(img);
		rear.append(b);
		card.append(front, rear);
		mover.append(card);
		if (count) fig.append(count);
		figs.push(/** @type {HTMLElement} */ (fig));
		movers.push(mover);
		cards.push(card);
		fronts.push(img);
	}
	if (!figs.length) return null;
	/** @type {Deck} */
	const deck = {
		article, figs, movers, cards, fronts,
		regular: fronts.map(i => i.getAttribute("src") || ""),
		bling: fronts.map(i => i.dataset.blingSrc || ""),
		token: {}, rects: [], box: { w: 0, h: 0 }, pile: { x: 0, y: 0 },
		depth: [], tilt: [],
	};
	decks.set(article, deck);
	return deck;
}

/* ---------------------------------------------------------------------
   where everything is */

/**
 * Every slot, relative to the article. Read off the figures, which never
 * carry a transform, plus the layout offsets of the mover and the card
 * inside them, which a transform does not touch either. So this is right
 * with the cards stacked, in flight, or at home.
 *
 * @param {Deck} deck
 */
function measure(deck) {
	const box = deck.article.getBoundingClientRect();
	deck.box = { w: box.width, h: box.height };
	deck.rects = deck.figs.map((fig, i) => {
		const f = fig.getBoundingClientRect();
		const m = deck.movers[i], c = deck.cards[i];
		return { x: f.left - box.left + m.offsetLeft + c.offsetLeft,
			y: f.top - box.top + m.offsetTop + c.offsetTop,
			w: c.offsetWidth, h: c.offsetHeight };
	});
	return box;
}

/**
 * The top card's corner for a pile at an origin, relative to the article.
 * The corners sit where the corner slots sit, so the pile is inside the
 * box's padding like everything else. "above" is off the top of the
 * screen, which is the one place that depends on the scroll position.
 *
 * @param {string} origin
 * @param {DOMRect} box   the article, in the viewport
 * @param {Deck} deck
 */
function pileAt(origin, box, deck) {
	const first = deck.rects[0];
	const w = first.w, h = first.h;
	const right = box.width - first.x - w;
	const bottom = box.height - first.y - h;
	const midX = box.width / 2 - w / 2;
	switch (origin) {
		case "top-left": return { x: first.x, y: first.y };
		case "top-right": return { x: right, y: first.y };
		case "bottom-left": return { x: first.x, y: bottom };
		case "bottom-right": return { x: right, y: bottom };
		case "above": return { x: midX, y: -box.top - h - 80 };
		default: return { x: midX, y: box.height / 2 - h / 2 };
	}
}

/**
 * Measure, place the pile, and decide the order. The pile is drawn by the
 * cards themselves: the first to be dealt sits on top, and each one
 * beneath is nudged a fraction of a pixel, which over two dozen cards
 * reads as the thickness of a deck. A little lean each, so it reads as a
 * stack of cards rather than a block.
 *
 * Cards are dealt in reading order, except that a slot the pile is sitting
 * on gets its card last: that card is the bottom of the pile, already in
 * place, and dealing it early would mean throwing it in under the stack.
 *
 * @param {Deck} deck
 * @param {string} origin
 */
function layout(deck, origin) {
	const box = measure(deck);
	deck.pile = pileAt(origin, box, deck);
	const p = deck.pile, w = deck.rects[0].w, h = deck.rects[0].h;
	const under = (/** @type {Rect} */ r) =>
		r.x < p.x + w - 4 && r.x + r.w > p.x + 4
		&& r.y < p.y + h - 4 && r.y + r.h > p.y + 4;
	const order = deck.rects.map((_, i) => i)
		.sort((a, b) => Number(under(deck.rects[a])) - Number(under(deck.rects[b])));
	deck.depth = [];
	order.forEach((card, d) => { deck.depth[card] = d; });
	deck.tilt = deck.rects.map(() => rand(-2.5, 2.5));
}

/** the transform that puts card i's corner at (x, y), turned a degrees
 * @param {Deck} deck @param {number} i @param {number} x @param {number} y
 * @param {number} a */
function to(deck, i, x, y, a) {
	const r = deck.rects[i];
	return `translate(${px(x - r.x)}, ${px(y - r.y)}) rotate(${deg(a)})`;
}

/** card i in its place on the pile
 * @param {Deck} deck @param {number} i @returns {Start} */
function start(deck, i) {
	const r = deck.rects[i], d = deck.depth[i];
	const tx = deck.pile.x + d * PILE.x - r.x;
	const ty = deck.pile.y + d * PILE.y - r.y;
	const tilt = deck.tilt[i];
	return { tx, ty, tilt,
		from: `translate(${px(tx)}, ${px(ty)}) rotate(${deg(tilt)})` };
}

/* ---------------------------------------------------------------------
   the moves */

/** Cancel everything in flight and clear every inline style.
 * @param {Deck} deck */
function clear(deck) {
	deck.token = {};
	for (const el of [...deck.movers, ...deck.cards, ...deck.figs]) {
		for (const a of el.getAnimations({ subtree: true })) a.cancel();
		el.style.transform = "";
		el.style.zIndex = "";
	}
}

/**
 * The count badges, all together: in once the deal is over, out before
 * anything takes the cards away. The stylesheet does the fade off the
 * article's data-counts attribute; this sets it, tells the stylesheet how
 * long to take at the current speed, and waits that long, so the beat
 * after an "out" starts on a bare strip.
 *
 * @param {Deck} deck
 * @param {boolean} on
 * @param {number} s
 */
async function counts(deck, on, s) {
	const { article } = deck;
	if (on === ("counts" in article.dataset)) return;
	article.style.setProperty("--deal-fade", `${Math.round(T.fade * s)}ms`);
	if (on) article.dataset.counts = "";
	else delete article.dataset.counts;
	await sleep(T.fade * s);
}

/**
 * Put every card on the pile, face down, with no animation.
 * @param {Deck} deck
 * @param {Opts} opts
 */
function stack(deck, opts) {
	clear(deck);
	delete deck.article.dataset.counts;
	deck.article.dataset.deal = "stacked";
	layout(deck, opts.origin);
	const n = deck.figs.length;
	deck.figs.forEach((fig, i) => {
		// the figure, not the mover, carries the order: the mover's
		// perspective makes it a stacking context of its own, so a z-index
		// on it would only ever order it against itself
		fig.style.zIndex = String(n - deck.depth[i]);
		deck.movers[i].style.transform = start(deck, i).from;
		deck.cards[i].dataset.down = "";
	});
}

/**
 * One beat: every card moves, and each is left where it ends up. The
 * animation fills both ways, the inline style is set to its last frame,
 * and only then is it cancelled, so nothing snaps. A card whose beat ends
 * at home also hands back its z-index, since it is in the grid again.
 *
 * @param {Deck} deck
 * @param {object} token
 * @param {(i: number) => Move} spec
 */
function moveAll(deck, token, spec) {
	return Promise.all(deck.movers.map((m, i) => {
		const { frames, end, delay, duration, easing = EASE, z, fill = "both" }
			= spec(i);
		if (z !== undefined) {
			// as the card starts moving, not as the beat starts: in the
			// shuffle that is the difference between the halves coming back
			// interleaved and the order changing while they are still out
			const order = () => {
				if (deck.token === token) deck.figs[i].style.zIndex = String(z);
			};
			if (delay > 0) setTimeout(order, delay);
			else order();
		}
		const a = m.animate(frames, { duration, delay, easing, fill });
		return a.finished.then(() => {
			if (deck.token !== token) return;
			m.style.transform = end;
			if (end === "") deck.figs[i].style.zIndex = "";
			a.cancel();
		}, () => {});
	}));
}

/** where card i is right now, as a keyframe
 * @param {Deck} deck @param {number} i */
function here(deck, i) {
	return { transform: deck.movers[i].style.transform || "translate(0px, 0px)" };
}

/**
 * The flight from the pile to the slot: three keyframes, the pile, the top
 * of the arc, and home. The arc bows to one side of the straight line,
 * away from the pile's centre, so cards dealt left curl one way and cards
 * dealt right curl the other, like a hand fanning them out; the card
 * spins a little the same way and rises toward the viewer at the apex.
 *
 * All three scale with the length of the flight. The card under the pile
 * is dealt last and travels only the few pixels from the bottom of the
 * stack to its slot; with a full spin it twisted on the spot and settled
 * back, which read as a glitch rather than a throw.
 *
 * @param {Start} s
 */
function flight(s) {
	const len = Math.hypot(s.tx, s.ty) || 1;
	// how much of a throw this is: a slot away is most of one, and
	// anything past two slots gets the whole arc
	const f = Math.min(len / 300, 1);
	// the unit normal to the line of flight
	const nx = -s.ty / len, ny = s.tx / len;
	const side = s.tx >= 0 ? 1 : -1;
	const bow = Math.min(len * 0.14, 48) * side;
	const spin = side * rand(10, 20) * f;
	const lift = 1 + (LIFT - 1) * f;
	const mx = s.tx * 0.5 + nx * bow;
	const my = s.ty * 0.5 + ny * bow;
	return [
		{ transform: `${s.from} scale(1)`,
			easing: "cubic-bezier(0.45, 0, 0.85, 0.55)" },
		{ transform: `translate(${px(mx)}, ${px(my)}) `
			+ `rotate(${deg(s.tilt * (1 - f * 0.5) + spin)}) scale(${lift.toFixed(3)})`,
			offset: 0.42,
			easing: "cubic-bezier(0.15, 0.6, 0.25, 1)" },
		{ transform: "translate(0px, 0px) rotate(0deg) scale(1)" },
	];
}

/**
 * When each card turns, in ms from the start of the turning.
 *
 * @param {string} flip
 * @param {Deck} deck
 * @param {number} s
 * @param {boolean} [inward]  the wave closes on the pile instead
 */
function turnDelays(flip, deck, s, inward = false) {
	const n = deck.cards.length;
	if (flip === "once") return deck.cards.map(() => 0);
	if (flip === "order") {
		return deck.cards.map((_, i) => deck.depth[i] * T.flipStagger * s);
	}
	if (flip === "random") {
		const order = shuffled(n);
		const delays = new Array(n);
		order.forEach((card, k) => { delays[card] = k * T.flipStagger * s; });
		return delays;
	}
	// ripple: by distance from the pile, so the wave spreads out from
	// where the cards came from, or closes in on where they are going
	const w = deck.rects[0].w, h = deck.rects[0].h;
	const cx = deck.pile.x + w / 2, cy = deck.pile.y + h / 2;
	const dist = deck.rects.map(r =>
		Math.hypot(r.x + w / 2 - cx, r.y + h / 2 - cy));
	const far = Math.max(...dist) || 1;
	return dist.map(d => ((inward ? far - d : d) / far) * T.ripple * s);
}

/**
 * Turn every card over. Resolves when the last one has.
 *
 * @param {Deck} deck
 * @param {object} token
 * @param {boolean} up
 * @param {number[]} delays
 * @param {number} s
 */
function turn(deck, token, up, delays, s) {
	const from = up ? 180 : 0, mid = 90, end = up ? 0 : 180;
	return Promise.all(deck.cards.map((c, i) => {
		const a = c.animate([
			{ transform: `rotateY(${from}deg) scale(1)` },
			{ transform: `rotateY(${mid}deg) scale(1.06)`, offset: 0.5 },
			{ transform: `rotateY(${end}deg) scale(1)` },
		], {
			duration: T.flip * s,
			delay: delays[i],
			easing: "ease-in-out",
			fill: "both",
		});
		return a.finished.then(() => {
			if (deck.token !== token) return;
			if (up) delete c.dataset.down;
			else c.dataset.down = "";
			a.cancel();
		}, () => {});
	}));
}

/**
 * From a waiting pile to a dealt strip: a beat of stillness, the throws,
 * a beat to settle, and the turn. The fronts have been hidden all this
 * time, so the turn waits for them to decode first, up to a point.
 *
 * @param {Deck} deck
 * @param {object} token
 * @param {Opts} opts
 * @param {number} s
 */
async function dealOut(deck, token, opts, s) {
	const stale = () => deck.token !== token;
	await frame();
	await sleep(T.hold * s);
	if (stale()) return;
	await moveAll(deck, token, i => ({
		frames: flight(start(deck, i)),
		end: "",
		delay: deck.depth[i] * T.stagger * s,
		duration: T.flight * s,
		easing: "linear",
	}));
	if (stale()) return;
	await sleep(T.settle * s);
	await Promise.race([
		Promise.all(deck.fronts.map(img => img.decode().catch(() => {}))),
		sleep(T.decode),
	]);
	if (stale()) return;
	await turn(deck, token, true, turnDelays(opts.flip, deck, s), s);
	if (stale()) return;
	deck.article.dataset.deal = "done";
	counts(deck, true, s);
}

/**
 * Every card back to the pile, face down, for a replay. The last card
 * dealt goes back first, so the pile builds in the order it will be dealt
 * from. A replay can land mid-deal, with cards in the air and half-turned;
 * each goes back from wherever it is, read off before the clear cancels
 * the animation holding it there. A matrix interpolates to a transform
 * list by decomposition, which is the right look here.
 *
 * @param {Deck} deck
 * @param {Opts} opts
 * @param {number} s
 */
async function gather(deck, opts, s) {
	const at = deck.movers.map(m => getComputedStyle(m).transform);
	const turned = deck.cards.map(c => getComputedStyle(c).transform);
	clear(deck);
	const token = deck.token;
	deck.article.dataset.deal = "dealing";
	layout(deck, opts.origin);
	const n = deck.figs.length;
	const timing = (/** @type {number} */ i) => ({
		duration: T.gather * s,
		delay: (n - 1 - deck.depth[i]) * 12 * s,
	});
	const turning = Promise.all(deck.cards.map((c, i) => {
		const a = c.animate([
			{ transform: turned[i] === "none" ? "rotateY(0deg)" : turned[i] },
			{ transform: "rotateY(180deg)" },
		], { ...timing(i), easing: EASE, fill: "both" });
		return a.finished.then(() => {
			if (deck.token !== token) return;
			c.dataset.down = "";
			a.cancel();
		}, () => {});
	}));
	await Promise.all([turning, moveAll(deck, token, i => ({
		frames: [
			{ transform: at[i] === "none" ? "translate(0px, 0px)" : at[i] },
			{ transform: start(deck, i).from },
		],
		end: start(deck, i).from,
		z: n - deck.depth[i],
		...timing(i),
	}))]);
	return token;
}

/**
 * The whole thing: from the pile, deal, settle, turn. Starts from wherever
 * the strip is: a waiting pile goes straight to the throws; a dealt strip
 * gathers first.
 *
 * @param {HTMLElement} article
 * @param {Opts} opts
 */
async function play(article, opts) {
	const deck = decks.get(article);
	if (!deck) return;
	const s = 1 / (Number(opts.speed) || 1);
	let token;
	if (article.dataset.deal === "stacked") {
		// the pile may have been measured at another width or origin
		stack(deck, opts);
		token = deck.token;
	} else {
		await counts(deck, false, s);
		token = await gather(deck, opts, s);
	}
	if (deck.token !== token) return;
	article.dataset.deal = "dealing";
	await dealOut(deck, token, opts, s);
}

/* ---------------------------------------------------------------------
   the shuffle, and the other prints */

/**
 * The shuffle, after deck.of.cards, taken slower. Every card flicks out to
 * one side or the other by a random third to a full card width, squaring
 * up as it goes, and comes straight back onto the stack at a new place in
 * it. Two stages of the same length, each card a few ms behind the one
 * above, so the stack splits into two ragged halves and snaps back
 * together. The second stage of the top card starts while the bottom card
 * is still on its way out, which is what makes it ripple rather than step.
 *
 * One pass, and the order changes for real: the slide to the corner that
 * follows puts the stack back in the order it deals from.
 *
 * @param {Deck} deck
 * @param {object} token
 * @param {number} s
 */
async function riffle(deck, token, s) {
	const n = deck.figs.length;
	const { w } = deck.rects[0];
	const ease = "cubic-bezier(0.645, 0.045, 0.355, 1)";
	/** @type {number[]} where each card lands in the stack, 0 the top */
	const at = [];
	shuffled(n).forEach((card, k) => { at[card] = k; });
	const out = deck.movers.map((_, i) => {
		const side = Math.random() < 0.5 ? -1 : 1;
		const x = deck.pile.x + at[i] * PILE.x
			+ side * rand(FLICK.min, FLICK.max) * w;
		return to(deck, i, x, deck.pile.y + at[i] * PILE.y, 0);
	});
	const back = deck.movers.map((_, i) =>
		to(deck, i, deck.pile.x + at[i] * PILE.x, deck.pile.y + at[i] * PILE.y, 0));
	const flick = moveAll(deck, token, i => ({
		frames: [here(deck, i), { transform: out[i] }],
		end: out[i],
		delay: at[i] * T.step * s,
		duration: T.flick * s,
		easing: ease,
	}));
	const home = moveAll(deck, token, i => ({
		frames: [{ transform: out[i] }, { transform: back[i] }],
		end: back[i],
		delay: (T.flick + at[i] * T.step) * s,
		duration: T.flick * s,
		easing: ease,
		z: n - at[i],
		fill: "forwards",
	}));
	await Promise.all([flick, home]);
}

/**
 * Put the other print behind every back. Waits for each to decode, and a
 * print that never arrives, offline or a dead link, leaves the scan that
 * was there.
 *
 * @param {Deck} deck
 * @param {string} art  "regular" or "bling"
 */
async function swapArt(deck, art) {
	await Promise.all(deck.fronts.map(async (img, i) => {
		const src = art === "bling" ? deck.bling[i] : deck.regular[i];
		const was = img.getAttribute("src") || "";
		if (!src || was === src) return;
		img.src = src;
		try {
			await Promise.race([img.decode(), sleep(T.remote).then(() => {
				throw new Error("slow");
			})]);
		} catch {
			img.src = was;
		}
	}));
	deck.article.dataset.art = art;
	// the switch reads the art on the table, so a run cut short by a replay
	// leaves it saying what is actually there
	deck.button?.setAttribute("aria-pressed", String(art === "bling"));
}

/**
 * The $$$: turn the strip over to the other prints without leaving it.
 * Face down in a wave that closes on the middle, onto a pile there, a
 * wash, the stack over to the corner, the faces swapped while nothing can
 * see them, and the deal again.
 *
 * @param {HTMLElement} article
 * @param {Opts} opts
 */
async function swap(article, opts) {
	const deck = decks.get(article);
	if (!deck || article.dataset.deal === "dealing") return;
	const art = article.dataset.art === "bling" ? "regular" : "bling";
	const s = 1 / (Number(opts.speed) || 1);
	// the prints come off the network, so ask for them now and let the
	// animation cover the wait
	if (art === "bling") {
		for (const src of deck.bling) if (src) new Image().src = src;
	}
	if (article.dataset.deal === "stacked") {
		// nothing on the table to gather up: swap, and deal
		await swapArt(deck, art);
		play(article, opts);
		return;
	}
	// claimed before the badges fade, so a second press during the fade
	// is the one that gets ignored
	article.dataset.deal = "dealing";
	await counts(deck, false, s);
	clear(deck);
	const token = deck.token;
	const stale = () => deck.token !== token;
	const n = deck.figs.length;
	layout(deck, "center");
	await turn(deck, token, false, turnDelays("ripple", deck, s, true), s);
	if (stale()) return;
	await moveAll(deck, token, i => ({
		frames: [here(deck, i), { transform: start(deck, i).from }],
		end: start(deck, i).from,
		delay: (n - 1 - deck.depth[i]) * 8 * s,
		duration: T.collapse * s,
		z: n - deck.depth[i],
	}));
	if (stale()) return;
	await riffle(deck, token, s);
	if (stale()) return;
	const was = deck.movers.map((_, i) => here(deck, i));
	layout(deck, opts.origin);
	await moveAll(deck, token, i => ({
		frames: [was[i], { transform: start(deck, i).from }],
		end: start(deck, i).from,
		delay: (n - 1 - deck.depth[i]) * 3 * s,
		duration: T.slide * s,
		easing: "cubic-bezier(0.65, 0, 0.35, 1)",
		z: n - deck.depth[i],
	}));
	if (stale()) return;
	await swapArt(deck, art);
	if (stale()) return;
	await dealOut(deck, token, opts, s);
}

/* ---------------------------------------------------------------------
   after the deal: the hover */

/**
 * A dealt card tilts toward the pointer, like picking it up by a corner.
 * The angle is read off the figure, which never moves, rather than the
 * card, whose box changes as it tilts and would feed back on itself.
 *
 * @param {Deck} deck
 */
function tilt(deck) {
	if (!matchMedia("(hover: hover) and (pointer: fine)").matches) return;
	const { article } = deck;
	deck.figs.forEach((fig, i) => {
		const card = deck.cards[i];
		fig.addEventListener("pointermove", e => {
			if (article.dataset.deal !== "done") return;
			const r = fig.getBoundingClientRect();
			const x = (e.clientX - r.left) / r.width - 0.5;
			const y = (e.clientY - r.top) / r.height - 0.5;
			card.style.transform = `rotateX(${deg(-y * 16)}) `
				+ `rotateY(${deg(x * 16)}) translateZ(14px)`;
		});
		fig.addEventListener("pointerleave", () => {
			if (article.dataset.deal !== "done") return;
			card.style.transform = "";
		});
	});
}

/* ---------------------------------------------------------------------
   wiring */

/** @returns {Opts} */
function load() {
	try {
		const saved = JSON.parse(localStorage.getItem(KEY) || "{}");
		return { ...DEFAULTS, ...saved };
	} catch {
		return { ...DEFAULTS };
	}
}

/** @param {Opts} opts */
function save(opts) {
	try {
		localStorage.setItem(KEY, JSON.stringify(opts));
	} catch {
		// private window, or storage off: the form still holds the values
	}
}

/**
 * The controls form, if the page has one.
 * @param {() => void} onChange
 * @returns {() => Opts}
 */
function controls(onChange) {
	const form = document.querySelector("[data-controls] form");
	let opts = load();
	if (!(form instanceof HTMLFormElement)) return () => opts;
	for (const [k, v] of Object.entries(opts)) {
		const el = form.elements.namedItem(k);
		if (el instanceof HTMLSelectElement) el.value = v;
	}
	const read = () => {
		const data = new FormData(form);
		opts = { ...DEFAULTS };
		for (const k of /** @type {(keyof Opts)[]} */ (Object.keys(DEFAULTS))) {
			opts[k] = String(data.get(k) ?? DEFAULTS[k]);
		}
		save(opts);
		return opts;
	};
	form.addEventListener("change", () => { read(); onChange(); });
	form.querySelector("[data-replay]")?.addEventListener("click", () => {
		read();
		onChange();
	});
	return () => opts;
}

function main() {
	const articles = /** @type {HTMLElement[]} */ (
		[...document.querySelectorAll("[data-decklist][data-deal-back]")]);
	const live = articles.filter(a => enhance(a));
	if (!live.length) return;
	const opts = controls(() => live.forEach(a => play(a, opts())));
	const still = matchMedia("(prefers-reduced-motion: reduce)").matches;

	for (const article of live) {
		const deck = /** @type {Deck} */ (decks.get(article));
		tilt(deck);
		article.dataset.art = "regular";

		// the $$$ in the heading above the strip
		const button = article.closest("section")?.querySelector("button[data-bling]");
		if (button instanceof HTMLElement) {
			if (deck.bling.some(Boolean)) {
				deck.button = button;
				button.addEventListener("click", () => swap(article, opts()));
			} else {
				button.hidden = true;
			}
		}

		if (still || !("IntersectionObserver" in window)) {
			article.dataset.deal = "done";
			article.dataset.counts = "";
			continue;
		}
		stack(deck, opts());
		// deal when a fifth of the strip is in view. once it has gone
		// entirely, and not before, since a fifth of it may still be on
		// screen, put the pile back so it deals again on its return.
		const io = new IntersectionObserver(entries => {
			for (const e of entries) {
				if (e.intersectionRatio >= 0.2
						&& article.dataset.deal === "stacked") {
					play(article, opts());
				} else if (!e.isIntersecting
						&& article.dataset.deal === "done") {
					stack(deck, opts());
				}
			}
		}, { threshold: [0, 0.2] });
		io.observe(article);
	}

	// a pile measured at one width is wrong at another. a card in the air
	// still lands at "no transform", so only a waiting pile is redone.
	let pending = 0;
	addEventListener("resize", () => {
		cancelAnimationFrame(pending);
		pending = requestAnimationFrame(() => {
			for (const article of live) {
				if (article.dataset.deal === "stacked") {
					stack(/** @type {Deck} */ (decks.get(article)), opts());
				}
			}
		});
	});
}

main();
