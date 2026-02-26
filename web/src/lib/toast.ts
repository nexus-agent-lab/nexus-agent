/**
 * Simple unified toast utility for global notifications.
 * Placeholder for a real library like sonner or react-hot-toast.
 */
export const toast = {
  error: (message: string) => {
    console.error(`[TOAST ERROR] ${message}`);
    if (typeof window !== "undefined") {
      window.alert(`❌ Error: ${message}`);
    }
  },
  success: (message: string) => {
    console.log(`[TOAST SUCCESS] ${message}`);
    if (typeof window !== "undefined") {
      window.alert(`✅ Success: ${message}`);
    }
  },
  info: (message: string) => {
    console.log(`[TOAST INFO] ${message}`);
    if (typeof window !== "undefined") {
      window.alert(`ℹ️ Info: ${message}`);
    }
  }
};
