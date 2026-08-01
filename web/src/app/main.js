// L4 composition root: load global styles and mount the app shell.
import "./app.css";
import App from "./App.svelte";
import { mount } from "svelte";

const app = mount(App, { target: document.getElementById("app") });

export default app;
