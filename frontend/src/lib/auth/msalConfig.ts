import { Configuration, LogLevel } from "@azure/msal-browser";

const tenantId = process.env.NEXT_PUBLIC_ENTRA_TENANT_ID ?? "";
const clientId = process.env.NEXT_PUBLIC_ENTRA_SPA_CLIENT_ID ?? "";

export const msalConfig: Configuration = {
  auth: {
    clientId,
    authority: `https://login.microsoftonline.com/${tenantId}`,
    redirectUri: typeof window !== "undefined" ? window.location.origin : "/",
    postLogoutRedirectUri: "/login",
  },
  cache: {
    cacheLocation: "sessionStorage",
    storeAuthStateInCookie: false,
  },
  system: {
    loggerOptions: {
      loggerCallback: (level, message, containsPii) => {
        if (containsPii) return;
        if (level === LogLevel.Error) console.error(message);
      },
    },
  },
};

// The scope the backend's App Registration exposes; must match
// ENTRA_API_APPLICATION_ID_URI/access_as_user on the backend (.env).
export const apiTokenRequest = {
  scopes: [process.env.NEXT_PUBLIC_ENTRA_API_SCOPE ?? ""],
};

export const isAuthDevMode = process.env.NEXT_PUBLIC_AUTH_DEV_MODE === "true";
