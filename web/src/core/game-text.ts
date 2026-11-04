// Font lookup 13BF850 maps these saved UTF-16 units before selecting a glyph.
// See data/name-glyph-evidence.json. Do not normalize other Unicode characters.
const glyphs: Record<string, string> = {
  "\u2472": "#",
  "\u2473": "?",
  "\u3251": "<",
  "\u3252": ">",
  "\u3253": "%",
  "\u3254": "＼",
  "\u3255": "¥",
};
const codes = Object.fromEntries(
  Object.entries(glyphs).map(([a, b]) => [b, a]),
);

export function displayGameText(text: string) {
  return text.replace(/[\u2472\u2473\u3251-\u3255]/g, (ch) => glyphs[ch]);
}

// Names entered in the editor use the matching game font codes. Unchanged names
// retain their original bytes, including any literal punctuation already saved.
export function storeGameText(text: string) {
  return text.replace(/[#?<>%＼¥]/g, (ch) => codes[ch]);
}
