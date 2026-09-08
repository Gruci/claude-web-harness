export const go = (theme: string) => {
  history.pushState(null, "", "#" + theme);
};
