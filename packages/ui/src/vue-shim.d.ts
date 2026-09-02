/** Allows TypeScript consumers to import Vue single-file components. */
declare module "*.vue" {
  const component: unknown;
  export default component;
}
