// @ts-check

import { VFM } from "@vivliostyle/vfm";
import rehypeMermaid from "rehype-mermaid";

/** @type {import('@vivliostyle/cli').VivliostyleConfigSchema} */
export default {
  title: "GreenInfraPlannerJP 操作マニュアル",
  author: "MIERUNE Inc.",
  size: "A4",
  language: "ja",
  theme: ["@vivliostyle/theme-academic@2.0.1", "styles/body.css"],
  image: "ghcr.io/vivliostyle/cli:9.7.1",
  entry: [
    {
      path: "contents/cover.html",
      title: "表紙",
      theme: ["@vivliostyle/theme-base@2.1.0", "styles/cover.css"],
    },
    {
      rel: "contents",
      theme: ["@vivliostyle/theme-academic@2.0.1", "styles/toc.css"],
    },
    {
      path: "contents/chap1.md",
      theme: ["@vivliostyle/theme-academic@2.0.1", "styles/body.css"],
    },
    {
      path: "contents/chap2.md",
      theme: ["@vivliostyle/theme-academic@2.0.1", "styles/body.css"],
    },
    {
      path: "contents/chap3.md",
      theme: ["@vivliostyle/theme-academic@2.0.1", "styles/body.css"],
    },
    {
      path: "contents/backcover.html",
      title: "裏表紙",
      theme: ["@vivliostyle/theme-base@2.1.0", "styles/backcover.css"],
    },
  ],
  output: ["document.pdf"],
  workspaceDir: ".vivliostyle", // directory which is saved intermediate files.
  toc: {
    title: "目次",
    sectionDepth: 3,
  },
  vfm: {
    math: true,
  },
  documentProcessor: (config, metadata) =>
    // 参考: https://zenn.dev/mura_mi/articles/4f08cc99f19887
    // @ts-ignore
    VFM(config, metadata).use(rehypeMermaid, { strategy: "img-svg" }),
};
