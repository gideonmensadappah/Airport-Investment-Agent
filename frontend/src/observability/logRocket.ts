import LogRocket from "logrocket";


export function initializeLogRocket(): void {
  const appId = import.meta.env.VITE_LOGROCKET_APP_ID?.trim();
  if (!appId) return;

  LogRocket.init(appId, {
    dom: {
      inputSanitizer: true,
      privateClassNameBlocklist: ["logrocket-private"],
    },
    network: {
      requestSanitizer: request => ({
        ...request,
        body: null,
        headers: {},
      }),
      responseSanitizer: () => null,
    },
  });
}
