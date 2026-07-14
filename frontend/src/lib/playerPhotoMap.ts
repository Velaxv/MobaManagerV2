/** Auto-gerado por scripts/fetch_player_photos.py */
/** Nick do seed -> /players/.... Ausente ou vazio = silhueta (sem foto de campeão). */
export const PLAYER_PHOTO_MAP: Record<string, string> = {
  "zynts": "/players/zynts.jpg",
  "STEPZ": "/players/stepz.jpg",
  "Kaze": "/players/kaze.jpg",
  "Rabelo": "/players/rabelo.jpg",
  "frosty": "/players/frosty.jpg",
  "Guigo": "/players/guigo.jpg",
  "Tatu": "/players/tatu.jpg",
  "Tutsz": "/players/tutsz.jpg",
  "JoJo": "/players/jojo.jpg",
  "Wizer": "/players/wizer.jpg",
  "Disamis": "/players/disamis.jpg",
  "Mireu": "/players/mireu.jpg",
  "ceo": "/players/ceo.jpg",
  "Kaiwing": "/players/kaiwing.jpg",
  "Zest": "/players/zest.jpg",
  "Feisty": "/players/feisty.jpg",
  "Duduhh": "/players/duduhh.jpg",
  "Ackerman": "/players/ackerman.jpg",
  "curty": "/players/curty.jpg",
  "Peach": "/players/peach.jpg",
  "cody": "/players/cody.jpg",
  "BAO": "/players/bao.jpg",
  "Momochi": "/players/momochi.jpg",
  "Xyno": "/players/xyno.jpg",
  "YoungJae": "/players/youngjae.jpg",
  "Bull": "/players/bull.jpg",
  "RedBert": "/players/redbert.jpg",
  "Robo": "/players/robo.jpg",
  "CarioK": "/players/cariok.jpg",
  "Keine": "/players/keine.jpg",
  "Trigger": "/players/trigger.jpg",
  "Kuri": "/players/kuri.jpg",
  "Devost": "/players/devost.jpg",
  "Booki": "/players/booki.jpg",
  "Enga": "/players/enga.jpg",
  "Snaker": "/players/snaker.jpg",
  "Toplop": "/players/toplop.jpg",
  "Samkz": "/players/samkz.jpg",
  "uZent": "/players/uzent.jpg",
  "sarolu": "/players/sarolu.jpg",
  "Morttheus": "/players/morttheus.jpg",
  "Drakehero": "/players/drakehero.jpg",
};

export function getPlayerPhotoUrl(name: string | undefined | null): string | null {
  if (!name) return null;
  const direct = PLAYER_PHOTO_MAP[name];
  if (direct) return direct;
  const lower = name.toLowerCase();
  for (const [k, v] of Object.entries(PLAYER_PHOTO_MAP)) {
    if (k.toLowerCase() === lower) return v;
  }
  return null;
}
