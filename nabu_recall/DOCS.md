# Nabu Recall — Home Assistant telepítés

A részletes magyar útmutató: [TELEPITES_HU.md](https://github.com/hollosipeti/nabu-recall/blob/main/TELEPITES_HU.md)

1. Az alkalmazást a saját adattárából telepítsd.
2. Add meg az OpenAI API-kulcsot és egy külön, legalább 32 karakteres **bridge_token** értéket.
3. Az alkalmazás indulása után az **OPEN WEB UI** gombbal megnyílik a diagnosztikai felület.
4. A Home Assistant `/config/custom_components/nabu_recall` mappába telepítsd a külön integrációt is, majd indítsd újra a HA-t.
5. Az integrációt csatlakoztasd az alkalmazáshoz, és válaszd ki a meglévő OpenAI Conversation HUN ügynököt. Azután válaszd ki a HUN Assistban a **Nabu Recall – memória** ügynököt.

A portokat ne publikáld LAN-ra. A napló titkosítatlan, 45 nap után törlődik; az AI által kivont tartós emlékek nem járnak le automatikusan.
