/**
 * Unified toast utility for global notifications.
 * Uses custom events to communicate with ToastContainer.
 */
export const toast = {
  error: (message: string) => {
    console.error(`[TOAST ERROR] ${message}`);
    if (typeof window !== "undefined") {
      const event = new CustomEvent("app-toast", { 
        detail: { message, type: "error", id: Math.random().toString(36).substr(2, 9) } 
      });
      window.dispatchEvent(event);
    }
  },
  success: (message: string) => {
    console.log(`[TOAST SUCCESS] ${message}`);
    if (typeof window !== "undefined") {
      const event = new CustomEvent("app-toast", { 
        detail: { message, type: "success", id: Math.random().toString(36).substr(2, 9) } 
      });
      window.dispatchEvent(event);
    }
  },
  info: (message: string) => {
    console.log(`[TOAST INFO] ${message}`);
    if (typeof window !== "undefined") {
      const event = new CustomEvent("app-toast", { 
        detail: { message, type: "info", id: Math.random().toString(36).substr(2, 9) } 
      });
      window.dispatchEvent(event);
    }
  }
};
