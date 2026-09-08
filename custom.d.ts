declare global {
  interface Window {
    process: {
      versions: {
        node: string | null;
      };
    };
  }
}

window.process = {versions: {node: null}};
