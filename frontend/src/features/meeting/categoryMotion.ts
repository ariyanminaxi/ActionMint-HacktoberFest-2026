export type Direction='l2r'|'r2l'|'t2b'|'b2t'|'tl2br'|'tr2bl'|'bl2tr'|'br2tl';
export const DIRECTIONS:readonly Direction[]=['l2r','r2l','t2b','b2t','tl2br','tr2bl','bl2tr','br2tl'];
export function pickDirection(previous:Direction|null,rand:()=>number=Math.random):Direction{
  const options=DIRECTIONS.filter(direction=>direction!==previous);
  return options[Math.min(options.length-1,Math.floor(Math.max(0,Math.min(.999999,rand()))*options.length))];
}
