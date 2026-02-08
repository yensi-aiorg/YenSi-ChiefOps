import { describe, it, expect } from "vitest";
import {
  formatNumber,
  formatPercentage,
  truncateText,
  getHealthScoreColor,
  getActivityLevelColor,
  cn,
} from "@/lib/utils";

describe("formatNumber", () => {
  it("formats large numbers with commas", () => {
    expect(formatNumber(1234567)).toBe("1,234,567");
  });

  it("handles zero", () => {
    expect(formatNumber(0)).toBe("0");
  });

  it("handles negative numbers", () => {
    expect(formatNumber(-1234)).toBe("-1,234");
  });
});

describe("formatPercentage", () => {
  it("formats percentage with default decimals", () => {
    expect(formatPercentage(75.5)).toBe("75.5%");
  });

  it("handles zero", () => {
    expect(formatPercentage(0)).toBe("0.0%");
  });

  it("handles 100%", () => {
    expect(formatPercentage(100)).toBe("100.0%");
  });
});

describe("truncateText", () => {
  it("truncates long text", () => {
    const long = "a".repeat(200);
    const result = truncateText(long, 50);
    expect(result.length).toBeLessThanOrEqual(53); // 50 + "..."
    expect(result.endsWith("...")).toBe(true);
  });

  it("does not truncate short text", () => {
    expect(truncateText("hello", 50)).toBe("hello");
  });
});

describe("getHealthScoreColor", () => {
  it("returns red for low scores", () => {
    const color = getHealthScoreColor(20);
    expect(color).toContain("red");
  });

  it("returns yellow for medium scores", () => {
    const color = getHealthScoreColor(55);
    expect(color).toContain("yellow");
  });

  it("returns teal for good scores", () => {
    const color = getHealthScoreColor(85);
    expect(color).toContain("teal");
  });
});

describe("getActivityLevelColor", () => {
  it("returns green for high activity", () => {
    const color = getActivityLevelColor("high");
    expect(color).toContain("green");
  });

  it("returns color for quiet", () => {
    const color = getActivityLevelColor("quiet");
    expect(color).toBeTruthy();
  });
});

describe("cn", () => {
  it("merges class names", () => {
    expect(cn("foo", "bar")).toBe("foo bar");
  });

  it("handles conditional classes", () => {
    const result = cn("base", false && "hidden", "visible");
    expect(result).toContain("base");
    expect(result).toContain("visible");
    expect(result).not.toContain("hidden");
  });
});
