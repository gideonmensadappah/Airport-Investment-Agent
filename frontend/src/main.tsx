import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { initializeLogRocket } from "./observability/logRocket";
import "./styles.css";


initializeLogRocket();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
