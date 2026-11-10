# Chalkless

**Einrichten:** Öffne deine KI-App (zum Beispiel Claude Cowork) mit einem neuen, leeren Ordner, kopiere diesen Text in den Chat und schick ihn ab. Alles Weitere macht der Agent; neue Versionen holt er sich später selbst.

```text
Bitte richte mir Chalkless ein, meinen Arbeitsbereich für die Unterrichtsplanung.
Paket: das Git-Repository https://github.com/Darius-Theodor/chalkless, Zweig pilot (öffentlich, ohne Anmeldung). Klone es mit git in einen temporären Ordner außerhalb dieses Ordners; darin liegt deine Anleitung.

Schreib mir von Anfang an auf Deutsch. Alles Technische machst du selbst; ich tippe
keine Befehle und nenne keine Pfade. Im Paket liegt eine Anleitung für dich:
setup/EINRICHTUNG.md. Lies sie zuerst, noch bevor du in diesem Ordner etwas anlegst,
und folge ihr Schritt für Schritt: Stell mir zuerst deine eine Frage und richte danach
alles ein.
```

(English copy text: [START-HIER.md](START-HIER.md#copy-text-english).)

Ein Ordner, in dem eine Lehrkraft mit einem KI-Agenten ihren Unterricht plant: Sie sagt frei, was sie für eine Stunde braucht, und bekommt ein fertiges Paket aus Stundenplanung, Arbeitsblatt mit Lösung und Folien, die zusammenpassen und gut aussehen. Dokumente kommen als PDF, Folien als Präsentation zum Öffnen im Browser. Dazu eine lokale Übersicht.

**Für Lehrkräfte:** Wie du danach damit arbeitest, steht kurz in [START-HIER.md](START-HIER.md).

> Version 0.4.0-dev ist ein **Entwicklungsstand** (schlanke Fassung im Test). Getestet wird mit Claude über die Kommandozeile unter Windows; in Claude Cowork gab es bisher nur einzelne Durchgänge von Hand, ChatGPT ist nicht geprüft. Was sich geändert hat, steht in [CHANGELOG.md](CHANGELOG.md).

Bitte keine Namen, Fotos oder Noten von Schülerinnen und Schülern in den Chat oder in den Ordner geben.

## Wie es funktioniert
- Du öffnest deine KI-App mit einem Ordner und schickst den Text aus START-HIER. Der Agent stellt eine Frage, die du in einem Satz beantwortest, holt sich dann Chalkless und richtet die Werkzeuge ein.
- Danach sagst du, was du brauchst. Der Agent baut das Paket, sieht sich seine Seiten selbst an, rechnet Lösungen nach und zeigt dir das Ergebnis mit einer kurzen Antwort. Du besserst im Gespräch nach.
- Eigene Vorgaben (Seminar, Schule) und eigene Beispiele gehen vor; dauerhafte Wünsche merkt er sich.

## Voraussetzungen
| Was | Wofür | Wenn es fehlt |
|---|---|---|
| Eine KI-App mit Zugriff auf einen lokalen Ordner | Der Agent arbeitet direkt im Ordner. | Geht nicht ohne. |
| Python 3.10 oder neuer (auf deinem Rechner oder in der Arbeitsumgebung der App) | Übersicht, PDF-Export, Prüfen der Seiten | Der Agent sagt dir einmal, was dann entfällt, und arbeitet mit dem Rest weiter. |
| Microsoft Edge oder Google Chrome | PDF-Export und Folienprüfung | Du druckst die Datei im Browser als PDF. |
| Git (optional) | Jeder fertige Schritt wird gesichert; „Mach das rückgängig“ | Kein Verlauf; der Agent sagt es dir einmal. |

Zusatzpakete für Seitenbilder und Folienprüfung richtet der Agent selbst ein. Du musst nichts konfigurieren.

## Aufbau
| Teil | Ordner | Inhalt |
|---|---|---|
| Kern (für alle gleich) | `kern/` und die Dateien im Hauptordner | Arbeitsregeln, Skills, Gestaltung, Übersicht, Werkzeuge |
| Rahmen | `rahmen/` | Lehrplan und Kalender deiner Region, je Baustein mit Prüfstatus; entsteht nach und nach |
| Dein Bereich | `profil/ vorlagen/ bereiche/ gedaechtnis/ review/ eingang/ beispiele/ archiv/` | gehört nur dir; deine Dokumente liegen in `bereiche/` |
| Einrichtungshilfe | `setup/` | nur bei der Einrichtung; der Agent entfernt sie, sie gehört nie zum Verlauf |

Der Kern wird bei einem Update als Ganzes ersetzt; Wünsche löst der Agent deshalb in deinem Bereich, nicht im Kern.

## Grenzen der Übersicht
Die Übersicht zeigt nur an; was du willst, sagst du im Chat. Es gibt sie in zwei Formen: neben dem Chat, wo die App das kann, sonst als Datei „Übersicht“ im Ordner (Doppelklick). Die Datei braucht kein Python auf deinem Rechner; der Agent schreibt sie nach jedem fertigen Schritt neu, und eine offene Seite zieht den neuen Stand von selbst nach.
- Im Seitenbereich der Desktop-Apps ist sie noch nicht praktisch geprüft, nur automatisch in Edge bei 400, 600 und 1280 px Breite.
- Kann der Seitenbereich keine PDFs anzeigen, bleibt die Vorschau leer; dann hilft „im eigenen Fenster öffnen“.
- Nach einem Update zeigt eine offene Übersicht den alten Stand, bis sie neu gestartet ist.

## Neue Versionen
Wurde Chalkless aus dem Git-Repository eingerichtet, schaut der Agent einmal pro Woche zu Beginn eines Chats nach, ob es eine neue Version gibt. Gibt es eine, erledigt er erst dein Anliegen, spielt sie danach ein und sagt es dir in einem Satz. Du kannst auch jederzeit sagen: „Spiel die neue Chalkless-Version ein.“ Wurde Chalkless aus einer ZIP-Datei eingerichtet, sagst du das, wenn es ein neues Paket gibt. Sonst lädst du das neue Paket herunter oder legst es in den Ordner „eingang“. In beiden Fällen ersetzt er nur den Kern, lässt alles Eigene unverändert, prüft deinen Arbeitsbereich und sagt dir kurz, was neu ist. „Mach das rückgängig“ nimmt auch ein Update als Ganzes zurück.

Kern-Version: `kern/VERSION`.
