# RFID Harava

## Lyhyt Kuvaus

RFID Harava on ohjelma, joka mahdollistaa RFID-tunnisteilla merkityn kirjastoaineiston massaskannauksen.
Se on suunniteltu käytettäväksi Koha-kirjastojärjestelmää käyttävissä kirjastoissa ja tukee kokoelmanhoidon tehtäviä.

![Screenshot](/docs/screenshot.PNG)

## Ohjelman lataaminen

Ohjelmapaketti löytyy tämän github sivun "Releases" -osiosta. Ohjelmapaketti pitää sisällään ohjelman ja ohjeet ohjelman käyttöönottoon, eri RFID-skannereiden konfigurointiin ja ohjelman käyttöön.

## Taustaa

Ohjelma kehitettiin alun perin Turun kaupunginkirjastossa opinnäytetyöprojektina toimivaksi prototyypiksi helpottamaan arkisia kokoelmanhoitoon liittyviä tehtäviä.

Ohjelmaa jatkokehitettiin myöhemmin Koha-Suomen projektissa toimimaan myös muissa kirjastokimpoissa ja lisäämällä siihen uusia ominaisuuksia. 

## Teknistä tietoa 

RFID Harava toimii FEIG ID ISC.PRH200 ja FEIG ID.PRH200-BW -skannereiden kanssa.

Ohjelma kommunikoi RFID-skannerin kanssa WiFi-verkon välityksellä portin 10001 kautta käyttäen TCP-protokollaa.

Ohjelma hakee nidetiedot Koha-kirjastojärjestelmästä REST-rajapinnan kautta käyttämällä kirjastojärjestelmässä tehtyjä API-tunnuksia.

Ohjelma tukee ISO 28560 ja Finnish Item -tietomallien mukaisesti kirjoitettuja RFID-tunnisteita joita käytetään kirjastoaineistossa.

## Ohjelmankääntäminen

Projektissa on mukana compiler.bat kääntöskripti, jolla saadaan käännettyä koodi suoritettavaksi tiedostoksi. Kääntöskripti vaatii toimiakseen pythonin ja projektissa käytetyt ulkoiset kirjastot. 

Kääntöskripti luo "Release" -kansion joka pitää sisällään ohjelman oikealla tiedostorakenteella ja "Ohjeet"-kansion. Kääntöskripti kopioi ohjelmaan liittyvät ohjeet "Ohjeet"-kansiosta. Jotta ohjelma saadaan toimimaan, täytyy ohjelman "Release\RfidHarava\Configs\config.ini" tiedostoon tehdä tarvittavat muutokset, tähän riittää tekstieditori esim. notepad.

Projektissa käytetty Python versio on 3.12

Projektissa käytetyt ulkoiset kirjastot:

| Kirjasto | Versio |
|-----------|--------|
| [PySide6](https://pypi.org/project/PySide6/) | 6.8.0.2 |
| [requests](https://pypi.org/project/requests/) | 2.31.0 |
| [pyinstaller](https://pypi.org/project/pyinstaller/) | 6.15.0 |



## Lisensonti

Lisensoitu EUPL:n nojalla.

Voit vapaasti käyttää, muokata ja jakaa ohjelmistoa lisenssin ehtojen mukaisesti.

## Kehittäjä

- **Robert Vallimägi** – Pääkehittäjä / Alkuperäinen tekijä  
