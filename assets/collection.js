/* Filtering and search for collection.html.
 *
 * Only this page loads it. Every card carries its own filterable values as
 * data attributes on the <article>, so nothing here reads text out of a cell:
 * the Set row holds an icon, a name, and a <small> card number, and parsing
 * that back into "SWSH04: Vivid Voltage" would break the first time a set
 * symbol went missing.
 *
 * Two independent filters, combined with AND:
 *
 *   click   one value per key. Clicking the same value again turns it off,
 *           clicking a different value of the same key swaps it.
 *   search  a fuzzy match on the name, so "gngr" finds Gengar.
 *
 * The contents list is kept in step with the cards, letter markers included,
 * so it never offers a jump to something that is not on screen. Clicking a
 * set name in the contents list does nothing on purpose.
 */
"use strict";

/* the clickable stat rows, and what to call each one in a chip */
const TERM = {
	set: "Set",
	rarity: "Rarity",
	type: "Type",
	stage: "Stage",
	tournament: "Tournament",
};

const main = document.querySelector("main");
const nav = document.querySelector("nav");
const cards = [...main.querySelectorAll("article[data-name]")];
const empty = main.querySelector("[data-empty]");
const bar = nav.querySelector("[data-active]");
const box = nav.querySelector("[data-search]");
const rows = [...nav.querySelectorAll("li")];

/* card -> its entry in the contents list */
const entries = new Map();
for (const card of cards) {
	const id = card.querySelector("[id]")?.id;
	const li = id && nav.querySelector(`li[data-for="${CSS.escape(id)}"]`);
	if (li) entries.set(card, li);
}

/* key -> the one value being filtered for */
const active = new Map();

/* letters, spaces, and accents all get in the way of typing a name fast */
function plain(s) {
	return (s || "")
		.normalize("NFD")
		.replace(/[\u0300-\u036f]/g, "")
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, "");
}

/* every letter of the query, in order, somewhere in the name. an empty query
   matches everything, which is what makes clearing the box free. */
function fuzzy(query, name) {
	let i = 0;
	for (const c of name) {
		if (c === query[i]) i++;
		if (i === query.length) break;
	}
	return i === query.length;
}

/* one chip per thing being filtered on. the × is decoration inside the button,
   not a control of its own: the whole chip is what turns the filter off. */
function chip(text, clear, cross = true) {
	const b = document.createElement("button");
	b.type = "button";
	b.append(text);
	if (cross) {
		const x = document.createElement("b");
		x.textContent = "×";
		b.append(x);
	}
	b.addEventListener("click", clear);
	return b;
}

/* a letter marker belongs on screen only while something under it does */
function markers() {
	let marker = null;
	let any = false;
	for (const li of rows) {
		if (li.hasAttribute("data-letter")) {
			if (marker) marker.hidden = !any;
			marker = li;
			any = false;
		} else if (!li.hidden) {
			any = true;
		}
	}
	if (marker) marker.hidden = !any;
}

function chips(shown) {
	bar.replaceChildren();
	const typed = box.value.trim();
	if (!active.size && !typed) {
		bar.hidden = true;
		return;
	}
	bar.hidden = false;

	const count = document.createElement("small");
	count.textContent = `${shown} of ${cards.length}`;
	bar.append(count);

	for (const [key, value] of active) {
		bar.append(chip(`${TERM[key]}: ${value}`, () => {
			active.delete(key);
			apply();
		}));
	}
	if (typed) {
		bar.append(chip(`Name: ${typed}`, () => {
			box.value = "";
			apply();
		}));
	}
	if (active.size + (typed ? 1 : 0) > 1) {
		bar.append(chip("Clear all", reset, false));
	}
}

function apply() {
	const query = plain(box.value);
	let shown = 0;
	for (const card of cards) {
		const ok = [...active].every(([k, v]) => card.dataset[k] === v)
			&& fuzzy(query, plain(card.dataset.name));
		card.hidden = !ok;
		const li = entries.get(card);
		if (li) li.hidden = !ok;
		if (ok) shown++;
	}
	markers();
	empty.hidden = shown > 0;
	chips(shown);
}

function reset() {
	active.clear();
	box.value = "";
	apply();
}

main.addEventListener("click", (e) => {
	/* the Tournament row can carry a footnote link. let it be a link. */
	if (e.target.closest("a")) return;
	const cell = e.target.closest("[data-filter]");
	if (!cell) return;
	const key = cell.dataset.filter;
	const value = cell.closest("article[data-name]")?.dataset[key];
	if (!value) return;
	if (active.get(key) === value) active.delete(key);
	else active.set(key, value);
	apply();
});

box.addEventListener("input", apply);
box.addEventListener("keydown", (e) => {
	if (e.key !== "Escape") return;
	box.value = "";
	apply();
});

/* a reload keeps whatever the browser restored in the search box */
apply();
