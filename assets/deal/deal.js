/* The deal: the deck-list strip and the card sections on every deck page.
 *
 * Progressive enhancement over what build_deck_html.py writes. Every
 * <figure> in the strip keeps its link, its scan, and its count badge; this
 * file wraps the scan in a two-faced card, stacks every card face down on a
 * pile in the middle (on a phone, in the top-left corner), shuffles it,
 * slides it to the corner, throws the cards one at a time to the slot the
 * grid already gave them, and turns them face up in a wave. That happens
 * once per load, when the whole of the waiting pile is first on screen.
 * Below the strip, each card section's scan starts face down too and turns
 * over the first time it comes into view.
 *
 * The grid is never repositioned. The flight is the FLIP trick: each slot
 * is measured where it already is, the card is pushed to the pile with a
 * transform, and animated back to none. So the strip wraps exactly as it
 * did without the script, and the last frame is the page as it was before
 * the script ran. Slots are measured off the figures, which never move,
 * and kept relative to the strip, so a measurement survives a scroll and a
 * card in mid-air. Resizing while the pile is waiting re-measures it;
 * resizing mid-air is left alone, since every card lands at "no transform"
 * regardless.
 *
 * The animations are Web Animations, not CSS transitions, because every
 * beat is sequenced off the last one's finished promises. Each animation
 * fills both ways and is cancelled only after the base style has been set
 * to its last frame, so nothing snaps. moveAll() is that pattern once, and
 * the deal, the collapse, the shuffle, and the slide are all calls to it.
 *
 * A deck with a Bling Deck has a $$$ in the corner of its Deck List
 * heading. The page carries both decks: the strip holds a figure for every
 * print of each, and a card section holds both scans and both stat blocks,
 * each tagged data-print. The root's data-showing says which deck is up,
 * and the stylesheet shows that one. Pressing the $$$ turns every card in
 * the strip face down, rebuilds the pile where shuffleAt() says, shuffles
 * it the way deck.of.cards does with a cut through it, slides it to the
 * corner, and there, with nothing face up, swaps the deck: the other set of
 * figures takes the pile's place, the strip eases to its new height, and
 * the deal runs again. The card sections turn face down when it is pressed
 * and turn up again, in the other deck's art, as each comes into view. A
 * link ending in #bling opens the page on the bling deck.
 *
 * Nothing moves on its own under prefers-reduced-motion: the strip and the
 * scans arrive as they are, and the $$$, an explicit ask, still deals.
 */
// @ts-check
"use strict";

/** milliseconds */
const T = {
	hold: 350,        // the pile sits still before the first throw
	flight: 560,      // one card, pile to slot
	stagger: 75,      // between one throw and the next
	settle: 220,      // after the last landing, before the first turn
	flip: 640,        // one card turning over
	ripple: 720,      // the whole wave, pile outward
	fade: 240,        // the count badges, in after the deal and out before
	                  // anything takes the cards away
	decode: 1500,     // the most a turn waits for the art it will show
	collapse: 480,    // the dealt strip onto the pile in the middle
	flick: 420,       // the shuffle: each card out to one side, and back
	step: 10,         // between one card's flick and the next
	tuck: 380,        // the cut: the top card, back in under the stack
	lift: 560,        // and the bottom card, lifted over onto the top
	cut: {            // when each starts back, after the halves start back
		tuck: 140,
		lift: 200,    // or later, if it would land before the last of them
	},
	slide: 520,       // the stack over to the corner it deals from
	resize: 450,      // the strip easing to the height of the other deck;
	                  // the stylesheet's --deal-resize, and a backstop here
};

/** every duration is multiplied by this: one place to slow it all down */
const SLOW = 1;

/** where the stack goes to be dealt, and the share of a card section's scan
 * that has to be on screen before it turns over */
const ORIGIN = "top-left";
const SEEN = 0.55;

/** the shuffle's flick: sideways by this share of the card's width. only
 * sideways: fanning the stack open vertically was tried and looked worse.
 * clear is how far the cut's two cards go: just past the edge of the stack,
 * so each reads as a card on its own rather than one of a half. beyond is
 * where the card left out waits when both cut cards go the same way, past
 * the other one */
const FLICK = { min: 0.32, max: 0.97, clear: 1.08, beyond: 1.7 };

/** a phone: the template's own breakpoint for its one-column layouts */
const PHONE = matchMedia("(width < 34em)");

/**
 * Where the pile is shuffled. On a big screen that is the middle of the
 * strip, and the stack slides over to the corner to be dealt. A phone's
 * strip is two cards wide and several screens tall, so there the shuffle
 * happens where the deal starts, in the top-left corner.
 */
const shuffleAt = () => PHONE.matches ? ORIGIN : "center";

/** how far a card in the pile sits from the one above it, in px */
const PILE = { x: 0.25, y: 0.3 };

/** how far a thrown card lifts toward the viewer at the top of its arc */
const LIFT = 1.1;

const EASE = "cubic-bezier(0.4, 0, 0.2, 1)";

const STILL = matchMedia("(prefers-reduced-motion: reduce)").matches;

/** @typedef {{x: number, y: number, w: number, h: number}} Rect */
/** @typedef {{tx: number, ty: number, tilt: number, from: string}} Start */
/** @typedef {"regular" | "bling"} Prints */
/**
 * @typedef {object} Fig  one figure in the strip, wrapped
 * @property {HTMLElement} fig
 * @property {HTMLElement} mover   the link, or a span standing in for one
 * @property {HTMLElement} card    the thing that turns
 * @property {HTMLImageElement} front
 */
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
 * @property {{regular: Fig[], bling: Fig[]}} sets  the strip's figures, by
 *                               the deck they belong to; a page with no
 *                               Bling Deck has only regular ones
 * @property {Prints} showing    which set is on the table
 * @property {HTMLElement[]} figs     the set on the table, as parallel lists
 * @property {HTMLElement[]} movers
 * @property {HTMLElement[]} cards
 * @property {HTMLImageElement[]} fronts
 * @property {HTMLElement} mark  an empty box over the waiting pile
 * @property {object} token      the run that owns the animations in flight
 * @property {Rect[]} rects      every slot, relative to the article
 * @property {{w: number, h: number}} box  the article
 * @property {{x: number, y: number}} pile the top card's corner, likewise
 * @property {number[]} depth    how far down the pile each card sits: 0 is
 *                               the top, and the first to be dealt
 * @property {number[]} tilt     each card's lean on the pile, in degrees
 * @property {HTMLElement} [button]  the $$$, when the deck has a Bling Deck
 */

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

/** wait for an image to be ready to show, but not for long */
const ready = (/** @type {HTMLImageElement} */ img) =>
	Promise.race([img.decode().catch(() => {}), sleep(T.decode)]);

/** a back for a card: the same picture everywhere */
function backFace(/** @type {string} */ src) {
	const rear = document.createElement("span");
	rear.dataset.face = "back";
	const b = document.createElement("img");
	b.src = src;
	b.alt = "";
	b.width = 365;
	b.height = 512;
	b.decoding = "async";
	rear.append(b);
	return rear;
}

/**
 * Wrap a scan in a two-faced card, face down, and return the card.
 *
 *   <span data-card data-down>       the thing that turns
 *     <span data-face="front"><img scan /></span>
 *     <span data-face="back"><img back /></span>
 *
 * @param {HTMLImageElement} img
 * @param {string} back
 */
function twoFaced(img, back) {
	const card = document.createElement("span");
	card.dataset.card = "";
	card.dataset.down = "";
	const front = document.createElement("span");
	front.dataset.face = "front";
	img.replaceWith(card);
	front.append(img);
	card.append(front, backFace(back));
	return card;
}

/* ---------------------------------------------------------------------
   which deck is up */

/**
 * Show one deck or the other, page-wide. The stylesheet does the showing:
 * every element tagged data-print and the price under the strip read the
 * root's data-showing. The frame and the switch are gild()'s, since they
 * move on the press. The card sections hear about it through the event.
 *
 * @param {Prints} prints
 */
function showPrints(prints) {
	const root = document.documentElement;
	if (prints === "bling") root.dataset.showing = "bling";
	else delete root.dataset.showing;
	document.dispatchEvent(new CustomEvent("deal:showing", { detail: prints }));
}

/**
 * The gold frame round the strip and the switch in its heading, set for
 * the deck asked for. They follow the press of the switch rather than the
 * swap, so both answer the moment it is pressed; data-showing waits for
 * the swap, since what it shows has to change while every card is face
 * down.
 *
 * The switch says where it goes: a purple $$$ while the regular deck is
 * up, and silver cents to come back down from the bling one. Its name for
 * a screen reader stays the same, with aria-pressed saying which way it is
 * set, since a toggle that renamed itself would read as a different
 * control each time.
 *
 * @param {Deck} deck @param {Prints} prints */
function gild(deck, prints) {
	const bling = prints === "bling";
	deck.article.toggleAttribute("data-gold", bling);
	const button = deck.button;
	if (!button) return;
	button.dataset.title ??= button.title;
	button.setAttribute("aria-pressed", String(bling));
	button.textContent = bling ? "\u00a2\u00a2\u00a2" : "$$$";
	button.title = bling ? "Back to the regular deck" : button.dataset.title;
}

/** start fetching a deck's scans now, hidden or not, so the shuffle covers
 * the wait: they are lazy so a page nobody switches never fetches them
 * @param {Fig[]} set */
function fetchSet(set) {
	for (const f of set) f.front.loading = "eager";
}

/* ---------------------------------------------------------------------
   the strip: the markup */

/**
 * Wrap every scan in the strip in a two-faced card.
 *
 *   <figure>
 *     <a>                             the mover
 *       <span data-card>              the thing that turns
 *     <span data-count />             the badge, flat on the slot
 *
 * The badge moves out of the link and after it, so it sits on the slot
 * rather than on the card: it never flies, never turns, and never tilts,
 * and the stylesheet keeps it invisible until the deal is over. It is
 * ours, not the card's, and that is how it should read. A figure with no
 * link gets a span to move instead.
 *
 * @param {HTMLElement} article
 * @returns {Deck | null}
 */
function enhance(article) {
	const back = article.dataset.dealBack;
	if (!back) return null;
	/** @type {{regular: Fig[], bling: Fig[]}} */
	const sets = { regular: [], bling: [] };
	for (const el of article.querySelectorAll("figure")) {
		const fig = /** @type {HTMLElement} */ (el);
		const img = fig.querySelector("img");
		if (!img || fig.querySelector("[data-card]")) continue;
		let mover = img.parentElement;
		if (!mover || mover === fig) {
			mover = document.createElement("span");
			fig.prepend(mover);
			mover.append(img);
		}
		mover.dataset.mover = "";
		const count = fig.querySelector("[data-count]");
		const card = twoFaced(img, back);
		if (count) fig.append(count);
		sets[fig.dataset.print === "bling" ? "bling" : "regular"]
			.push({ fig, mover, card, front: img });
	}
	if (!sets.regular.length) return null;
	// an empty box laid over the waiting pile, for the observer to watch:
	// the shuffle starts when all of the pile is on screen, which is not
	// the same moment as some of the strip being on screen
	const mark = document.createElement("span");
	mark.dataset.dealPile = "";
	mark.setAttribute("aria-hidden", "true");
	article.append(mark);
	/** @type {Deck} */
	const deck = {
		article, sets, showing: "regular", mark,
		figs: [], movers: [], cards: [], fronts: [],
		token: {}, rects: [], box: { w: 0, h: 0 }, pile: { x: 0, y: 0 },
		depth: [], tilt: [],
	};
	use(deck, "regular");
	return deck;
}

/** put one set on the table, as the parallel lists everything else reads
 * @param {Deck} deck @param {Prints} prints */
function use(deck, prints) {
	const set = deck.sets[prints];
	deck.showing = prints;
	deck.figs = set.map(f => f.fig);
	deck.movers = set.map(f => f.mover);
	deck.cards = set.map(f => f.card);
	deck.fronts = set.map(f => f.front);
}

/* ---------------------------------------------------------------------
   the strip: where everything is */

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
 * The top card's corner for a pile, relative to the article: the corner
 * slot, or the middle of the strip, or of its first screenful where it is
 * taller than the screen, as on a phone, where the middle of the strip is
 * a screen or more below its heading.
 *
 * @param {string} where  "top-left" or "center"
 * @param {DOMRect} box   the article, in the viewport
 * @param {Deck} deck
 */
function pileAt(where, box, deck) {
	const first = deck.rects[0];
	const { w, h } = first;
	if (where === "top-left") return { x: first.x, y: first.y };
	const bottom = box.height - first.y - h;
	const mid = Math.min(box.height, innerHeight) / 2 - h / 2;
	return { x: box.width / 2 - w / 2, y: Math.min(Math.max(mid, first.y), bottom) };
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
 * @param {string} where
 */
function layout(deck, where) {
	const box = measure(deck);
	deck.pile = pileAt(where, box, deck);
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
   the strip: the moves */

/** Cancel everything in flight on a set of figures, and clear every inline
 * style off them.
 * @param {Fig[]} set */
function wipe(set) {
	for (const { fig, mover, card } of set) {
		for (const el of [fig, mover, card]) {
			for (const a of el.getAnimations()) a.cancel();
			el.style.transform = "";
			el.style.zIndex = "";
		}
		delete fig.dataset.lift;
	}
}

/** a fresh run, with the table cleared of the last one
 * @param {Deck} deck */
function clear(deck) {
	deck.token = {};
	wipe(deck.sets[deck.showing]);
}

/**
 * The count badges, all together: in once the deal is over, out before
 * anything takes the cards away. The stylesheet does the fade off the
 * article's data-counts attribute; this sets it, tells the stylesheet how
 * long to take, and waits that long, so the beat after an "out" starts on
 * a bare strip.
 *
 * @param {Deck} deck
 * @param {boolean} on
 */
async function counts(deck, on) {
	const { article } = deck;
	if (on === ("counts" in article.dataset)) return;
	article.style.setProperty("--deal-fade", `${Math.round(T.fade * SLOW)}ms`);
	if (on) article.dataset.counts = "";
	else delete article.dataset.counts;
	await sleep(T.fade * SLOW);
}

/** every card on the table onto the pile, face down, ordered, at once
 * @param {Deck} deck */
function place(deck) {
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
 * Put every card on the pile where it is shuffled, face down, with no
 * animation: where it waits to be shuffled, taken to the corner, and dealt.
 * @param {Deck} deck
 */
function stack(deck) {
	clear(deck);
	delete deck.article.dataset.counts;
	deck.article.dataset.deal = "stacked";
	layout(deck, shuffleAt());
	place(deck);
	// the marker the shuffle waits on, laid over the pile
	const { w, h } = deck.rects[0];
	Object.assign(deck.mark.style, { left: px(deck.pile.x), top: px(deck.pile.y),
		width: px(w), height: px(h) });
}

/**
 * Change which set of figures is on the table. The other deck's figures
 * take the place of these in the strip at once, so this runs only when
 * every card is face down on the pile and nothing can see it happen; the
 * caller puts the new set on the pile in the same frame. The strip's
 * height is held at what it was and eased to what it is now, since the
 * two decks need not fill the same number of rows.
 *
 * @param {Deck} deck
 * @param {Prints} prints
 */
function switchTo(deck, prints) {
	const { article } = deck;
	wipe(deck.sets[deck.showing]);
	for (const f of deck.sets[deck.showing]) f.card.dataset.down = "";
	article.style.height = "";
	const was = article.getBoundingClientRect().height;
	use(deck, prints);
	showPrints(prints);
	const now = article.getBoundingClientRect().height;
	if (STILL || Math.abs(now - was) < 1) return;
	article.style.height = px(was);
	article.getBoundingClientRect();
	article.style.height = px(now);
	const done = () => {
		article.style.height = "";
		article.removeEventListener("transitionend", end);
	};
	const end = (/** @type {TransitionEvent} */ e) => {
		if (e.target === article && e.propertyName === "height") done();
	};
	article.addEventListener("transitionend", end);
	setTimeout(done, T.resize * SLOW + 200);
}

/**
 * The stack from wherever it is to the corner it deals from, the bottom
 * card first, so the top card arrives last and stays on top.
 *
 * @param {Deck} deck
 * @param {object} token
 */
function slide(deck, token) {
	const n = deck.figs.length;
	const was = deck.movers.map((_, i) => here(deck, i));
	layout(deck, ORIGIN);
	return moveAll(deck, token, i => ({
		frames: [was[i], { transform: start(deck, i).from }],
		end: start(deck, i).from,
		delay: (n - 1 - deck.depth[i]) * 3 * SLOW,
		duration: T.slide * SLOW,
		easing: "cubic-bezier(0.65, 0, 0.35, 1)",
		z: n - deck.depth[i],
	}));
}

/**
 * One beat: every card moves, and each is left where it ends up. The
 * animation fills both ways, the inline style is set to its last frame,
 * and only then is it cancelled, so nothing snaps. A card whose beat ends
 * at home also hands back its z-index, since it is in the grid again.
 *
 * @param {Deck} deck
 * @param {object} token
 * @param {(i: number) => Move | null} spec  null leaves card i where it is
 */
function moveAll(deck, token, spec) {
	return Promise.all(deck.movers.map((m, i) => {
		const move = spec(i);
		if (!move) return undefined;     // this card sits the beat out
		const { frames, end, delay, duration, easing = EASE, z, fill = "both" }
			= move;
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
 * When each card turns, in ms from the start of the turning: by distance
 * from the pile, so the wave spreads out from where the cards came from,
 * or closes in on where they are going.
 *
 * @param {Deck} deck
 * @param {boolean} [inward]
 */
function rippleDelays(deck, inward = false) {
	const w = deck.rects[0].w, h = deck.rects[0].h;
	const cx = deck.pile.x + w / 2, cy = deck.pile.y + h / 2;
	const dist = deck.rects.map(r =>
		Math.hypot(r.x + w / 2 - cx, r.y + h / 2 - cy));
	const far = Math.max(...dist) || 1;
	return dist.map(d => ((inward ? far - d : d) / far) * T.ripple * SLOW);
}

/** the keyframes of one card turning over, with a little rise at the edge
 * @param {boolean} up */
function turnFrames(up) {
	const from = up ? 180 : 0, end = up ? 0 : 180;
	return [
		{ transform: `rotateY(${from}deg) scale(1)` },
		{ transform: "rotateY(90deg) scale(1.06)", offset: 0.5 },
		{ transform: `rotateY(${end}deg) scale(1)` },
	];
}

/**
 * Turn every card on the table over. Resolves when the last one has.
 *
 * @param {Deck} deck
 * @param {object} token
 * @param {boolean} up
 * @param {number[]} delays
 */
function turn(deck, token, up, delays) {
	return Promise.all(deck.cards.map((c, i) => {
		const a = c.animate(turnFrames(up), {
			duration: T.flip * SLOW,
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
 * From the pile at the corner to a dealt strip: a beat of stillness, the
 * throws, a beat to settle, and the turn. The fronts have been hidden all
 * this time, so the turn waits for them to decode first, up to a point.
 *
 * @param {Deck} deck
 * @param {object} token
 */
async function dealOut(deck, token) {
	const stale = () => deck.token !== token;
	await frame();
	await sleep(T.hold * SLOW);
	if (stale()) return;
	await moveAll(deck, token, i => ({
		frames: flight(start(deck, i)),
		end: "",
		delay: deck.depth[i] * T.stagger * SLOW,
		duration: T.flight * SLOW,
		easing: "linear",
	}));
	if (stale()) return;
	await sleep(T.settle * SLOW);
	await Promise.all(deck.fronts.map(ready));
	if (stale()) return;
	await turn(deck, token, true, rippleDelays(deck));
	if (stale()) return;
	deck.article.dataset.deal = "done";
	counts(deck, true);
}

/**
 * The opening, once per load: the pile waiting face down where it is
 * shuffled gets a beat, the shuffle, the slide to the corner, and the deal.
 * Not stacked again first: the resize handler keeps a waiting pile
 * measured, and a fresh stack would give every card a new lean in view.
 *
 * @param {Deck} deck
 */
async function play(deck) {
	if (deck.article.dataset.deal !== "stacked") return;
	deck.token = {};
	const token = deck.token;
	const stale = () => deck.token !== token;
	deck.article.dataset.deal = "dealing";
	await frame();
	await sleep(T.hold * SLOW);
	if (stale()) return;
	await riffle(deck, token);
	if (stale()) return;
	await slide(deck, token);
	if (stale()) return;
	await dealOut(deck, token);
}

/* ---------------------------------------------------------------------
   the strip: the shuffle */

/**
 * The shuffle, after deck.of.cards, taken slower, with a cut running
 * through it so it reads as the order changing. Every back is the same
 * picture, so a riffle on its own only ever looks like the stack splitting
 * and closing; nothing shows a card going anywhere. So two cards do it in
 * plain sight, while the riffle is still going on around them.
 *
 *   the riffle  every other card flicks out to one side or the other by a
 *               third to a full card width, squaring up, and comes straight
 *               back onto the stack at a new place in it, each a few ms
 *               behind the one above, so the stack splits into two ragged
 *               halves and snaps back together
 *   the top     the top card slides off the left of the stack, over the
 *               left-hand half, and as the halves start back it ducks and
 *               slides in under everything
 *   the bottom  the bottom card slides out from under the right-hand half,
 *               further than it goes, and as the halves start back it is
 *               picked up, shadow and all, carried over them, and laid on
 *               top, landing last
 *
 * Each of the two changes its place in the order at the start of its move
 * back, while the halves are still out, so its edge passes over or under
 * theirs at that moment. The duck and the lift are timed to land on that
 * instant so it reads as the card going under or coming up, not as a
 * glitch. Where the page is too narrow, the cards go only as far as they
 * can without handing it a sideways scrollbar, and so do the flicks. With
 * no room on the left at all, as in the corner of a phone's strip, the top
 * card peels off to the right instead, over the right-hand half, and the
 * card left out waits further along, under everything; the left-hand
 * flicks have nowhere to go, so that half stays put and the split reads
 * as one half pulled off to the right.
 *
 * The order changes for real; the slide to the corner that follows puts
 * the stack back in the order it deals from.
 *
 * @param {Deck} deck
 * @param {object} token
 */
async function riffle(deck, token) {
	const s = SLOW;
	const n = deck.figs.length;
	const { w } = deck.rects[0];
	const ease = "cubic-bezier(0.645, 0.045, 0.355, 1)";
	// how far a card whose corner is at x can go to one side before it runs
	// off the page, which would give the page a scrollbar for a moment
	const box = deck.article.getBoundingClientRect();
	const page = document.documentElement.clientWidth;
	const reach = (/** @type {number} */ side, /** @type {number} */ d,
		/** @type {number} */ x) =>
		Math.max(0, Math.min(d, side < 0
			? box.left + x - 4
			: page - (box.left + x + w) - 4));
	const spot = (/** @type {number} */ k) =>
		({ x: deck.pile.x + k * PILE.x, y: deck.pile.y + k * PILE.y });
	const clear = FLICK.clear * w;
	const later = (/** @type {number} */ ms, /** @type {() => void} */ fn) =>
		setTimeout(() => { if (deck.token === token) fn(); }, ms);

	// the top card goes under and the bottom card goes on top; every other
	// card riffles. a deck too small for a cut just riffles.
	const down = n > 2 ? deck.depth.indexOf(0) : -1;
	const up = n > 2 ? deck.depth.indexOf(n - 1) : -1;
	const rest = deck.movers.map((_, i) => i)
		.filter(i => i !== up && i !== down);
	/** @type {number[]} where each riffled card lands, 0 the top */
	const at = [];
	shuffled(rest.length).forEach((j, k) => { at[rest[j]] = k; });

	const top = spot(0), bottom = spot(n - 1);
	// the top card peels off the left and the bottom card is left out on
	// the right. where there is no room on the left, as in the corner of a
	// phone's strip, both go right: the top card just past the stack, over
	// the right-hand half, and the bottom card beyond it, under everything.
	const cramped = reach(-1, clear, top.x) < 0.6 * w;
	const offX = cramped                                 // the top card, out
		? top.x + reach(1, clear, top.x)
		: top.x - reach(-1, clear, top.x);
	const asideX = bottom.x                              // the bottom card
		+ reach(1, cramped ? FLICK.beyond * w : clear, bottom.x);
	const out = deck.movers.map((_, i) => {
		if (i === down) return to(deck, i, offX, top.y, 0);
		if (i === up) return to(deck, i, asideX, bottom.y, 0);
		const { x, y } = spot(at[i]);
		const side = Math.random() < 0.5 ? -1 : 1;
		const d = reach(side, rand(FLICK.min, FLICK.max) * w, x);
		return to(deck, i, x + side * d, y, 0);
	});
	const back = deck.movers.map((_, i) => {
		const { x, y } = spot(at[i] ?? 0);
		return to(deck, i, x, y, 0);
	});

	const flick = moveAll(deck, token, i => ({
		frames: [here(deck, i), { transform: out[i] }],
		end: out[i],
		delay: (i === down ? 0 : i === up ? 4 : at[i]) * T.step * s,
		duration: T.flick * s,
		easing: ease,
		// the top card is on top already and stays above the left-hand half
		// on its way out; the bottom card stays under the right-hand half
		z: i === down ? n + 1 : i === up ? 0 : undefined,
	}));
	const home = moveAll(deck, token, i => rest.includes(i) ? {
		frames: [{ transform: out[i] }, { transform: back[i] }],
		end: back[i],
		delay: (T.flick + at[i] * T.step) * s,
		duration: T.flick * s,
		easing: ease,
		z: n - at[i],
		fill: "forwards",
	} : null);
	if (down < 0 || up < 0) {
		await Promise.all([flick, home]);
		return;
	}

	// the cut, timed off the riffle: both cards start back while the halves
	// are still coming home, and the lifted card lands after the last of
	// them, so the shuffle ends on it. "forwards", so neither holds its first
	// frame through its delay and drags its card off the flick before it.
	const closed = T.flick + (rest.length - 1) * T.step + T.flick;
	const tuckAt = T.flick + T.cut.tuck;
	const liftAt = Math.max(T.flick + T.cut.lift, closed + 120 - T.lift);

	const under = to(deck, down, bottom.x, bottom.y, 0);
	const ducked = to(deck, down, offX + (bottom.x - offX) * 0.25,
		top.y + (bottom.y - top.y) * 0.25, 0);
	const onTop = to(deck, up, top.x - PILE.x, top.y - PILE.y, 0);
	const along = (/** @type {number} */ f, /** @type {number} */ a) =>
		to(deck, up, asideX + (top.x - asideX) * f,
			bottom.y + (top.y - bottom.y) * f, a);

	// under everything, a touch smaller straight away so the drop in the
	// order reads as the card ducking, then flat again as it settles. under
	// every riffled card, but over the card left out, which it lies across
	// when both have gone right, and never lower than 0: a figure below
	// that would sink under the strip's own background.
	const tuck = moveAll(deck, token, i => i === down ? {
		frames: [
			{ transform: `${out[i]} scale(1)` },
			{ transform: `${ducked} scale(0.95)`, offset: 0.25 },
			{ transform: `${under} scale(1)` },
		],
		end: under,
		delay: tuckAt * s,
		duration: T.tuck * s,
		z: 1,
		fill: "forwards",
	} : null);
	// over everything, lifted toward the viewer at once, so the rise in the
	// order reads as the card being picked up, and carried over the halves
	const lift = moveAll(deck, token, i => i === up ? {
		frames: [
			{ transform: `${out[i]} scale(1)` },
			{ transform: `${along(0.15, -2)} scale(1.07)`, offset: 0.15 },
			{ transform: `${along(0.6, -3)} scale(1.08)`, offset: 0.6 },
			{ transform: `${onTop} scale(1)` },
		],
		end: onTop,
		delay: liftAt * s,
		duration: T.lift * s,
		z: n + 2,
		fill: "forwards",
	} : null);
	later(liftAt * s, () => { deck.figs[up].dataset.lift = ""; });
	await Promise.all([flick, home, tuck, lift]);
	// the shadow eases back down as it lands, which reads as it settling
	if (deck.token === token) delete deck.figs[up].dataset.lift;
}

/* ---------------------------------------------------------------------
   the strip: the $$$ */

/**
 * The $$$: deal the other deck without leaving the strip. Face down in a
 * wave that closes on where the pile will be, onto the pile there, the
 * shuffle, the stack over to the corner, the deck swapped there while
 * nothing can see it, and the deal again. A pile still waiting for the
 * opening just swaps, and plays.
 *
 * @param {Deck} deck
 */
async function swap(deck) {
	const { article } = deck;
	if (article.dataset.deal === "dealing") return;
	/** @type {Prints} */
	const prints = deck.showing === "bling" ? "regular" : "bling";
	// the gold frame answers the press itself, not the swap seconds later,
	// so it is the first thing to move
	gild(deck, prints);
	fetchSet(deck.sets[prints]);
	document.dispatchEvent(new CustomEvent("deal:press"));
	if (article.dataset.deal === "stacked") {
		switchTo(deck, prints);
		stack(deck);
		play(deck);
		return;
	}
	// claimed before the badges fade, so a second press during the fade
	// is the one that gets ignored
	article.dataset.deal = "dealing";
	await counts(deck, false);
	clear(deck);
	const token = deck.token;
	const stale = () => deck.token !== token;
	const n = deck.figs.length;
	layout(deck, shuffleAt());
	await turn(deck, token, false, rippleDelays(deck, true));
	if (stale()) return;
	await moveAll(deck, token, i => ({
		frames: [here(deck, i), { transform: start(deck, i).from }],
		end: start(deck, i).from,
		delay: (n - 1 - deck.depth[i]) * 8 * SLOW,
		duration: T.collapse * SLOW,
		z: n - deck.depth[i],
	}));
	if (stale()) return;
	await riffle(deck, token);
	if (stale()) return;
	await slide(deck, token);
	if (stale()) return;
	switchTo(deck, prints);
	layout(deck, ORIGIN);
	place(deck);
	await dealOut(deck, token);
}

/* ---------------------------------------------------------------------
   the strip: after the deal, the hover */

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
	for (const { fig, card } of [...deck.sets.regular, ...deck.sets.bling]) {
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
	}
}

/* ---------------------------------------------------------------------
   the card sections */

/**
 * @typedef {object} Scan  one scan in a card section, wrapped
 * @property {HTMLElement} link   the <a data-art>, opening it full size
 * @property {HTMLElement} card
 * @property {HTMLImageElement} front
 * @property {string} print       "regular", "bling", or "" when the card
 *                                has no bling print and shows either way
 * @property {Animation | null} anim  a turn in flight
 */
/**
 * @typedef {object} Spot  one card section's scan column
 * @property {Scan[]} scans
 * @property {boolean} seen       enough of it on screen to turn over
 */

/** the scan a card section shows with the deck that is up
 * @param {Spot} spot */
function shownScan(spot) {
	const showing = document.documentElement.dataset.showing || "regular";
	return spot.scans.find(s => !s.print || s.print === showing) || null;
}

/**
 * Turn a scan over, up or down. The front is decoded first on the way up,
 * up to a point, so it never turns up blank.
 *
 * @param {Scan} scan
 * @param {boolean} up
 */
async function flipScan(scan, up) {
	scan.anim?.cancel();
	if (up) await ready(scan.front);
	const a = scan.card.animate(turnFrames(up), {
		duration: T.flip * SLOW, easing: "ease-in-out", fill: "both",
	});
	scan.anim = a;
	try {
		await a.finished;
	} catch {
		return;           // cancelled: whoever cancelled it set the face
	}
	if (up) delete scan.card.dataset.down;
	else scan.card.dataset.down = "";
	a.cancel();
	scan.anim = null;
}

/** a scan face down at once, whatever it was doing
 * @param {Scan} scan */
function coverScan(scan) {
	scan.anim?.cancel();
	scan.anim = null;
	scan.card.dataset.down = "";
}

/**
 * Every card section's scan, face down, turning over the first time most
 * of it is on screen: scrolling down the page, or landing on it from a
 * link. Once up it stays up for the load, until the $$$ deals the other
 * deck: then every scan turns face down, the ones in view turning over and
 * the rest at once, and each turns up again in the other deck's art the
 * next time it comes into view. Under reduced motion nothing turns, and
 * the stylesheet alone swaps the art.
 */
function cardSections() {
	const links = /** @type {HTMLElement[]} */ (
		[...document.querySelectorAll("article > aside > a[data-art]")]);
	if (!links.length) return;
	const back = document.querySelector("[data-deal-back]")
		?.getAttribute("data-deal-back") || "./assets/card-back.png";
	if (STILL || !("IntersectionObserver" in window)) {
		// lifts the stylesheet's face-down placeholder
		for (const link of links) link.dataset.flip = "still";
		return;
	}
	/** @type {Map<Element, Spot>} */
	const spots = new Map();
	for (const link of links) {
		const img = link.querySelector("img");
		const aside = link.parentElement;
		if (!img || !aside) continue;
		const card = twoFaced(img, back);
		link.dataset.flip = "";
		/** @type {Scan} */
		const scan = { link, card, front: img, print: link.dataset.print || "", anim: null };
		const spot = spots.get(aside) || { scans: [], seen: false };
		spot.scans.push(scan);
		spots.set(aside, spot);
	}
	// from a press of the $$$ until the other deck is up, nothing turns up:
	// a scan in view would only turn up in the art that is leaving
	let waiting = false;
	const reveal = (/** @type {Spot} */ spot) => {
		const scan = shownScan(spot);
		if (!waiting && spot.seen && scan && "down" in scan.card.dataset && !scan.anim) {
			flipScan(scan, true);
		}
	};
	const io = new IntersectionObserver(entries => {
		for (const e of entries) {
			const spot = spots.get(e.target);
			if (!spot) continue;
			spot.seen = e.intersectionRatio >= SEEN;
			if (spot.seen) reveal(spot);
		}
	}, { threshold: [0, SEEN] });
	for (const aside of spots.keys()) io.observe(aside);

	document.addEventListener("deal:press", () => {
		waiting = true;
		for (const spot of spots.values()) {
			const shown = shownScan(spot);
			for (const scan of spot.scans) {
				if (spot.seen && scan === shown && !("down" in scan.card.dataset)) {
					flipScan(scan, false);
				} else {
					coverScan(scan);
				}
			}
		}
	});
	document.addEventListener("deal:showing", () => {
		waiting = false;
		for (const spot of spots.values()) {
			// the scan that just left is hidden now; it starts down, so it
			// turns up again if its deck comes back
			const shown = shownScan(spot);
			for (const scan of spot.scans) if (scan !== shown) coverScan(scan);
			reveal(spot);
		}
	});
}

/* ---------------------------------------------------------------------
   wiring */

function main() {
	// the card sections listen for the strip, so they are wired up first
	cardSections();

	const article = /** @type {HTMLElement | null} */ (
		document.querySelector("[data-decklist][data-deal-back]"));
	const deck = article && enhance(article);
	if (!deck) return;
	const hasBling = deck.sets.bling.length > 0;

	// the $$$ in the corner of the Deck List heading
	const button = /** @type {HTMLElement | null} */ (
		document.querySelector("h3 button[data-bling]"));
	if (button) {
		if (hasBling) {
			deck.button = button;
			button.addEventListener("click", () => swap(deck));
		} else {
			button.hidden = true;
		}
	}

	// a fresh request for #bling opens on the bling deck
	if (hasBling && location.hash === "#bling") {
		use(deck, "bling");
		fetchSet(deck.sets.bling);
		gild(deck, "bling");
		showPrints("bling");
	}

	tilt(deck);
	if (STILL || !("IntersectionObserver" in window)) {
		// nothing deals on its own, so the cards start the way they end up:
		// face up, in the grid. the $$$ still deals, from here.
		for (const f of [...deck.sets.regular, ...deck.sets.bling]) delete f.card.dataset.down;
		deck.article.dataset.deal = "done";
		deck.article.dataset.counts = "";
		return;
	}
	stack(deck);
	// the pile waits face down where it is shuffled, and the opening starts
	// once all of it is on screen and a little way up from the bottom edge,
	// so it does not play against the edge. once, and never again: the
	// observer goes as soon as it has fired. the threshold is a hair under
	// 1, since a box on a fractional pixel can top out just short of it.
	const io = new IntersectionObserver(entries => {
		for (const e of entries) {
			if (e.intersectionRatio >= 0.98 && deck.article.dataset.deal === "stacked") {
				io.disconnect();
				play(deck);
			}
		}
	}, { threshold: [0.98], rootMargin: "0px 0px -12% 0px" });
	io.observe(deck.mark);

	// a pile measured at one width is wrong at another. a card in the air
	// still lands at "no transform", so only a waiting pile is redone.
	let pending = 0;
	addEventListener("resize", () => {
		cancelAnimationFrame(pending);
		pending = requestAnimationFrame(() => {
			if (deck.article.dataset.deal === "stacked") stack(deck);
		});
	});
}

main();
