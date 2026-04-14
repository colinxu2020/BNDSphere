export const cssVar = (name: string) =>
  getComputedStyle(document.documentElement).getPropertyValue(name).trim();

export const theme = {
  primary: () => cssVar('--color-primary') || '#0066ff',
  accent: () => cssVar('--color-accent') || '#ff7a59',
  text: () => cssVar('--color-text') || '#111827',
};

export default theme;
