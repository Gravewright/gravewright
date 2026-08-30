import { guides as ptBrGuides } from "../locales/pt-br.guides.mjs";
import { guides as enGuides } from "../locales/en.guides.mjs";
import { guides as esGuides } from "../locales/es.guides.mjs";
import { interfaceText } from "../locales/interface.mjs";

export const DEFAULT_LOCALE = "en";
export const SUPPORTED_LOCALES = ["en", "pt-br", "es"];

export const localeCatalogs = {
  en: { ui: interfaceText.en, guides: enGuides },
  "pt-br": { ui: interfaceText["pt-br"], guides: ptBrGuides },
  es: { ui: interfaceText.es, guides: esGuides },
};
