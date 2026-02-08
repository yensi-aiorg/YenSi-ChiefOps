import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { App } from "@/App";
import "@/styles/globals.css";

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error(
    'Root element not found. Ensure there is a <div id="root"></div> in your index.html.',
  );
}

createRoot(rootElement).render(
  <StrictMode>
    <BrowserRouter>
      <App />
      <Toaster
        position="top-right"
        gutter={8}
        containerClassName="mt-16"
        toastOptions={{
          duration: 4000,
          style: {
            background: "#1e293b",
            color: "#f1f5f9",
            borderRadius: "0.75rem",
            padding: "12px 16px",
            fontSize: "0.875rem",
            boxShadow:
              "0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)",
          },
          success: {
            iconTheme: {
              primary: "#07c7b1",
              secondary: "#f1f5f9",
            },
          },
          error: {
            iconTheme: {
              primary: "#ef4444",
              secondary: "#f1f5f9",
            },
          },
        }}
      />
    </BrowserRouter>
  </StrictMode>,
);
