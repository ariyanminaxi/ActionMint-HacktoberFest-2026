import {describe,it,expect} from 'vitest';
import {CATEGORIES,VISIBLE_CATEGORIES} from './categories';
import {pickDirection,type Direction} from './categoryMotion';

const allowed:Direction[]=['l2r','r2l','t2b','b2t','tl2br','tr2bl','bl2tr','br2tl'];

describe('category registry and transition direction',()=>{
  it('contains unique ids and stable A/B asset paths',()=>{
    expect(new Set(CATEGORIES.map(x=>x.id)).size).toBe(CATEGORIES.length);
    for(const category of CATEGORIES){
      expect(category.frames).toEqual([`/assets/categories/${category.id}-a.png`,`/assets/categories/${category.id}-b.png`]);
    }
    expect(VISIBLE_CATEGORIES.map(x=>x.id)).toEqual(['overview','decisions','actions','people','timeline','transcript','ask','recap']);
  });
  it('picks only allowed directions and never repeats consecutively',()=>{
    let previous:Direction|null=null;let seed=7;
    for(let i=0;i<200;i++){
      seed=(seed*16807)%2147483647;
      const direction=pickDirection(previous,()=>seed/2147483647);
      expect(allowed).toContain(direction);
      if(previous)expect(direction).not.toBe(previous);
      previous=direction;
    }
  });
});
