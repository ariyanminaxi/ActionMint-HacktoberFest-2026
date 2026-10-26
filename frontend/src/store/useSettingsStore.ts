import {create} from 'zustand';
export type CategoryAnimationMode='on'|'reduced'|'off';
type Settings={
  theme:'dark'|'light';
  lowEffects:boolean;
  categoryAnimations:CategoryAnimationMode;
  setTheme:(theme:'dark'|'light')=>void;
  setLowEffects:(enabled:boolean)=>void;
  setCategoryAnimations:(mode:CategoryAnimationMode)=>void;
};
const read=(key:string,legacy:string|null=null)=>typeof localStorage==='undefined'?null:localStorage.getItem(key)??(legacy?localStorage.getItem(legacy):null);
const storedAnimation=read('actionmint.categoryAnimations');
const initialAnimation:CategoryAnimationMode=storedAnimation==='reduced'||storedAnimation==='off'?storedAnimation:'on';
export const useSettingsStore=create<Settings>(set=>({
  theme:read('actionmint.theme','morrow.theme')==='light'?'light':'dark',
  lowEffects:read('actionmint.lowEffects','morrow.lowEffects')==='true',
  categoryAnimations:initialAnimation,
  setTheme:theme=>{localStorage.setItem('actionmint.theme',theme);set({theme})},
  setLowEffects:lowEffects=>{localStorage.setItem('actionmint.lowEffects',String(lowEffects));set({lowEffects})},
  setCategoryAnimations:categoryAnimations=>{localStorage.setItem('actionmint.categoryAnimations',categoryAnimations);set({categoryAnimations})},
}));
