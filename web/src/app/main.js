// L4 composition root (placeholder). The real app shell — router, providers, and
// real-adapter injection — lands in P6. For now it just proves the build/serve path.
import App from "./App.svelte";
import { mount } from "svelte";

const app = mount(App, { target: document.getElementById("app") });

export default app;
