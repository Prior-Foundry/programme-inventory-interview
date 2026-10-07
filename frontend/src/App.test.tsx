import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import App from "./App";

describe("interview starter", () => {
  it("renders the three empty workflow stages", () => {
    const markup = renderToStaticMarkup(<App />);
    expect(markup).toContain("Programme inventory");
    expect(markup).toContain("Document library");
    expect(markup).toContain("Programme setup");
  });
});
