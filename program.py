from flask import Flask, request, jsonify, render_template_string
import random
import math

app = Flask(__name__)

# ==========================================
# SILNIK FIZYCZNY I TELEMETRYCZNY
# ==========================================

class Tor:
    def __init__(self, nazwa, dlugosc, material, nachylenie_lukow, szerokosc, ubicie, bronowanie, nawodnienie):
        self.nazwa = nazwa
        self.dlugosc = dlugosc
        self.material = material
        self.nachylenie_lukow = nachylenie_lukow
        self.szerokosc = szerokosc
        self.ubicie = ubicie
        self.bronowanie = bronowanie
        self.nawodnienie = nawodnienie
        
        self.efektywna_twardosc = max(0.0, (self.ubicie - self.bronowanie) / 100.0)
        self.efektywna_luznosc = max(0.0, (self.bronowanie - self.ubicie) / 100.0)
        
        self.kohezja = max(0.4, 1.0 - (abs(60.0 - self.nawodnienie) * 0.012))

        if self.material == 'granit': baza_mat = 0.75 
        elif self.material == 'sjenit': baza_mat = 0.65 
        elif self.material == 'lupek': baza_mat = 0.45 
        else: baza_mat = 0.65

        self.mu_bazowe = baza_mat * self.kohezja * (1.0 + (self.efektywna_luznosc * 0.5))

        self.koleiny = 0.0
        self.potencjal_odsypu = 0.2 + (self.efektywna_luznosc * 1.5) 
        self.wsp_zmeczenia = 0.5 + (self.efektywna_luznosc * 1.5) + (self.nawodnienie * 0.01)

        if self.efektywna_luznosc > 0.4:
            self.przyczepnosc_krawaznik = self.mu_bazowe * 1.4
            self.przyczepnosc_banda = self.mu_bazowe * 0.85
        elif self.efektywna_twardosc > 0.6:
            self.przyczepnosc_krawaznik = self.mu_bazowe * 0.95
            self.przyczepnosc_banda = self.mu_bazowe * 1.05
        else:
            self.przyczepnosc_krawaznik = self.mu_bazowe * 1.15
            self.przyczepnosc_banda = self.mu_bazowe * 0.95
            
    def aktualizuj_tor(self):
        przyrost_kolein = (0.01 + (self.efektywna_luznosc * 0.04)) * (self.nawodnienie / 50.0)
        self.koleiny = min(1.0, self.koleiny + przyrost_kolein)
        przesuniecie_materialu = 0.05 * self.potencjal_odsypu * self.kohezja
        self.przyczepnosc_krawaznik -= (przesuniecie_materialu * 0.5) 
        self.przyczepnosc_banda += przesuniecie_materialu


class Motocykl:
    def __init__(self, przelozenie, opona):
        self.przelozenie = przelozenie 
        self.opona = opona 
        self.stan_bieznika = 100.0
        self.temperatura = 50.0 
        
    def degraduj_i_nagrzewaj(self, agresja, tor_twardosc):
        mnoznik_temp = 1.0 + (tor_twardosc * 1.5)
        agresja_wsp = agresja / 100.0
        if self.opona == 'Anlas':
            self.temperatura += (agresja_wsp * 0.8) * mnoznik_temp
            self.stan_bieznika -= (agresja_wsp * 1.5) 
        else:
            self.temperatura += (agresja_wsp * 0.4) * mnoznik_temp
            self.stan_bieznika -= (agresja_wsp * 0.6)
        self.stan_bieznika = max(0.0, self.stan_bieznika)
        
    def pobierz_wsp_trakcji(self):
        if self.opona == 'Anlas':
            kary_temp = 0.0 if 70 < self.temperatura < 110 else 0.20
            baza = 1.10 if self.stan_bieznika > 50 else 0.70 
            return max(0.3, baza - kary_temp)
        else:
            return max(0.6, 1.0 - ((100.0 - self.stan_bieznika) * 0.001))


class Zawodnik:
    def __init__(self, imie, pole, refleks, gaz, balans, zmysl, agresja, taktyka, motocykl):
        self.imie = imie
        self.pole = pole
        self.refleks = float(refleks)
        self.kontrola_gazu = float(gaz)
        self.balans = float(balans)
        self.zmysl_mechaniczny = float(zmysl)
        self.agresja = float(agresja)
        self.taktyka = taktyka
        self.motocykl = motocykl
        
        self.stamina = 100.0
        self.wybrana_linia = 'krawaznik'
        self.aktywny = True
        self.powod_wykluczenia = ""
        self.czas_calkowity = 0.0 
        self.telemetria = []

    def to_dict(self, miejsce, pkt):
        return {
            "imie": self.imie,
            "kask": self.pole,
            "aktywny": self.aktywny,
            "powod_wykluczenia": self.powod_wykluczenia,
            "czas_calkowity": self.czas_calkowity,
            "stamina": self.stamina,
            "miejsce": miejsce,
            "pkt": pkt,
            "telemetria": self.telemetria,
            "motocykl": {
                "opona": self.motocykl.opona,
                "stan_bieznika": self.motocykl.stan_bieznika,
                "temperatura": self.motocykl.temperatura
            }
        }


OPISY = {
    "START": ["🚀 Atomowy start! {z} wysuwa się na czoło.", "💨 Świetny refleks! {z} zakłada rywali na dojeździe."],
    "TASMA": ["❌ KATASTROFA! {z} wjeżdża w taśmę!"],
    "DEFEKT": ["🔧 DEFEKT! Silnik nie wytrzymał u {z}!"],
    "OBRONA": ["🛡️ {ryw} zamyka ścieżkę! {z} musi szukać innej linii.", "🛡️ {z} przymknął gaz, by nie wjechać w rywala ({ryw})."],
    "ATAK": ["🔥 Co za manewr! {z} mija rywala ({ryw}) na dystansie!", "🔥 Profesor! {z} nakrywa rywala ({ryw})!"],
    "POGON": ["⚡ {z} napędza się niesamowicie! Zbliża się do rywala!"]
}

def symuluj_wyscig(dane_toru, dane_zawodnikow):
    tor = Tor(**dane_toru)
    zawodnicy = []
    for d in dane_zawodnikow:
        moto = Motocykl(float(d['zebatka_tyl'])/14.0, d['opona'])
        z = Zawodnik(d['imie'], d['kask'], d['refleks'], d['gaz'], d['balans'], d['zmysl'], d['agresja'], d['taktyka'], moto)
        zawodnicy.append(z)

    wydarzenia = []
    def dodaj_wydarzenie(typ, czas, tekst):
        wydarzenia.append({"typ": typ, "czas": float(czas), "tekst": tekst})

    # START
    for z in zawodnicy:
        szansa_tasma = 0.04 - (z.refleks * 0.0004)
        if random.random() < szansa_tasma:
            z.aktywny = False
            z.powod_wykluczenia = "Taśma"
            dodaj_wydarzenie("tasma", 0.0, OPISY["TASMA"][0].replace("{z}", z.imie))
            z.telemetria.append({"sector": 0, "time": 0.0, "line": "krawaznik"})
            continue
            
        baza_reakcji = 0.35 
        reakcja = baza_reakcji - (z.refleks * 0.002) + random.uniform(0.0, 0.04)
        
        baza_bonusu = {'A': 0.0, 'B': 0.03, 'C': 0.05, 'D': 0.07}
        if tor.efektywna_luznosc > 0.5:
            baza_bonusu = {'A': 0.08, 'B': 0.04, 'C': 0.0, 'D': 0.02} 
            
        mnoznik = random.uniform(0.9, 1.2) 
        z.czas_calkowity = reakcja + (baza_bonusu[z.pole] * mnoznik)
        z.telemetria.append({"sector": 0, "time": z.czas_calkowity, "line": "krawaznik"})

    aktywni = [z for z in zawodnicy if z.aktywny]
    aktywni.sort(key=lambda x: x.czas_calkowity) 
    if aktywni:
        dodaj_wydarzenie("start", aktywni[0].czas_calkowity, random.choice(OPISY["START"]).replace("{z}", aktywni[0].imie))

    globalny_sektor = 0
    sektory = ["prosta", "wejscie", "szczyt", "wyjscie"] * 2
    baza_sektora = (tor.dlugosc / 8.0) / 23.5 

    for okr in range(1, 5):
        if not aktywni: break
        
        for sektor_typ in sektory:
            globalny_sektor += 1
            for z in aktywni:
                if not z.aktywny: continue
                
                if sektor_typ == "prosta" and random.random() < 0.0003:
                    z.aktywny = False
                    z.powod_wykluczenia = "Defekt"
                    dodaj_wydarzenie("defekt", z.czas_calkowity, OPISY["DEFEKT"][0].replace("{z}", z.imie))
                    continue
                        
                z.wybrana_linia = 'banda' if z.zmysl_mechaniczny > 75 and tor.przyczepnosc_banda > tor.przyczepnosc_krawaznik else 'krawaznik'
                przyczepnosc_efektywna = tor.przyczepnosc_banda if z.wybrana_linia == 'banda' else tor.przyczepnosc_krawaznik
                trakcja = z.motocykl.pobierz_wsp_trakcji()
                przelozenie = z.motocykl.przelozenie
                zysk = 0.0
                
                if sektor_typ == "prosta":
                    wsp_dlugosci = tor.dlugosc / 320.0
                    zysk = ((4.5 - przelozenie) * 0.018 * wsp_dlugosci) + ((z.kontrola_gazu / 100.0) * 0.04) 
                    if przelozenie > 4.3 and tor.dlugosc > 360 and random.random() < 0.03:
                        dodaj_wydarzenie("warn", z.czas_calkowity, f"⚠️ Silnik {z.imie} wyje na prostej! (odcinka)")
                elif sektor_typ == "wejscie":
                    zysk = ((z.balans / 100.0) * 0.03) + ((z.zmysl_mechaniczny / 100.0) * 0.02) 
                elif sektor_typ == "szczyt":
                    bonus_banking = tor.nachylenie_lukow * 0.001
                    if z.taktyka == 'klasyczna': zysk = ((z.balans / 100.0) * 0.04 + bonus_banking) * przyczepnosc_efektywna * trakcja
                    else: zysk = -0.005 + bonus_banking 
                elif sektor_typ == "wyjscie":
                    kara_za_ciezar = 0.0 if przelozenie >= 4.1 else (tor.efektywna_luznosc * 0.02)
                    zysk_przysp = (przelozenie - 3.7) * 0.025 * (1.0 + tor.efektywna_luznosc) - kara_za_ciezar
                    if przelozenie < 3.9 and tor.efektywna_luznosc > 0.5 and random.random() < 0.03:
                         dodaj_wydarzenie("warn", z.czas_calkowity, f"⚠️ Motocykl {z.imie} muli na wyjściu z łuku!")
                    if z.taktyka == 'late_apex': zysk = (zysk_przysp * 1.3) + ((z.kontrola_gazu / 100.0) * 0.05) * przyczepnosc_efektywna * trakcja
                    else: zysk = zysk_przysp + ((z.kontrola_gazu / 100.0) * 0.03) * przyczepnosc_efektywna * trakcja

                z.stamina = max(0, z.stamina - (tor.wsp_zmeczenia * (z.agresja / 100.0)))
                if z.stamina < 30.0: zysk -= 0.020 

                z.motocykl.degraduj_i_nagrzewaj(z.agresja, tor.efektywna_twardosc)
                z.czas_calkowity += baza_sektora - zysk + random.uniform(0.005, 0.015)
                z.telemetria.append({"sector": globalny_sektor, "time": z.czas_calkowity, "line": z.wybrana_linia})

            aktywni = [z for z in aktywni if z.aktywny]
            aktywni.sort(key=lambda x: x.czas_calkowity)
            
            atakowali = set()
            for i in range(1, len(aktywni)):
                z = aktywni[i]
                rywal = aktywni[i-1]
                strata = z.czas_calkowity - rywal.czas_calkowity
                
                if 0.10 < strata < 0.25 and random.random() < 0.05 and z.zmysl_mechaniczny > 85:
                    dodaj_wydarzenie("info", z.czas_calkowity, OPISY["POGON"][0].replace("{z}", z.imie))

                if strata < 0.08 and z.imie not in atakowali:
                    atakowali.add(z.imie)
                    szansa_ataku = 0.2 + (z.agresja * 0.002) + (z.zmysl_mechaniczny * 0.002)
                    if okr > 1: szansa_ataku *= 0.5 
                    
                    if random.random() < szansa_ataku:
                        sila_ataku = (z.agresja * 1.2) + z.kontrola_gazu + z.zmysl_mechaniczny + random.randint(0, 30)
                        sila_obrony = (rywal.agresja * 1.2) + rywal.balans + rywal.zmysl_mechaniczny + random.randint(0, 30)
                        
                        if sila_ataku > sila_obrony:
                            z.czas_calkowity = rywal.czas_calkowity - 0.010 
                            rywal.czas_calkowity += random.uniform(0.04, 0.08) 
                            dodaj_wydarzenie("atak", z.czas_calkowity, random.choice(OPISY["ATAK"]).replace("{z}", z.imie).replace("{ryw}", rywal.imie))
                            z.telemetria[-1]["time"] = z.czas_calkowity
                            rywal.telemetria[-1]["time"] = rywal.czas_calkowity
                        else:
                            z.czas_calkowity += random.uniform(0.02, 0.05)
                            if random.random() < 0.3:
                                dodaj_wydarzenie("obrona", z.czas_calkowity, random.choice(OPISY["OBRONA"]).replace("{z}", z.imie).replace("{ryw}", rywal.imie))
                            z.telemetria[-1]["time"] = z.czas_calkowity
            
            aktywni.sort(key=lambda x: x.czas_calkowity)
            tor.aktualizuj_tor()
        
    punkty_tab = [3, 2, 1, 0]
    wyniki = []
    for i, z in enumerate(zawodnicy):
        miejsce = aktywni.index(z) + 1 if z.aktywny else 4
        pkt = punkty_tab[miejsce - 1] if z.aktywny else 0
        wyniki.append(z.to_dict(miejsce, pkt))
        
    wyniki.sort(key=lambda x: (not x['aktywny'], x['czas_calkowity']))
    wydarzenia.sort(key=lambda x: x['czas'])

    return {"wyniki": wyniki, "wydarzenia": wydarzenia}


# ==========================================
# APLIKACJA FLASK I INTERFEJS WEBOWY (HTML)
# ==========================================

INDEX_HTML = """
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Symulator Żużlowy - PRO API</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .custom-scrollbar::-webkit-scrollbar { width: 8px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: #1e293b; border-radius: 8px; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #475569; border-radius: 8px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #64748b; }
    </style>
</head>
<body class="bg-slate-900 text-slate-200 font-sans min-h-screen">
    <div class="max-w-6xl mx-auto p-6 space-y-6">
        
        <!-- Header -->
        <div class="flex items-center justify-between bg-slate-800 p-5 rounded-xl border border-slate-700 shadow-xl">
            <div class="flex items-center space-x-4">
                <div class="w-12 h-12 bg-orange-600 rounded-full flex items-center justify-center font-bold text-2xl shadow-lg">Ż</div>
                <h1 class="text-3xl font-bold tracking-wider">SYMULATOR <span class="text-orange-500">PRO</span></h1>
            </div>
            <div class="text-slate-400 font-mono">Silnik: Python Flask | Render: JS</div>
        </div>

        <div id="setup-view" class="grid md:grid-cols-3 gap-6">
            <!-- Pasek boczny: Tor i Akcje -->
            <div class="md:col-span-1 space-y-4">
                <div class="bg-slate-800 p-5 rounded-xl border border-slate-700 shadow-lg">
                    <h2 class="text-xl font-bold mb-4 border-b border-slate-700 pb-2">Wybór Toru</h2>
                    <select id="track-select" class="w-full bg-slate-700 border border-slate-600 p-3 rounded-lg text-white mb-4">
                        <option value="gorzow">Gorzów (Optymalny, 329m)</option>
                        <option value="wroclaw">Wrocław (Ciężka Kopa, 352m)</option>
                        <option value="krosno">Krosno (Długi Beton, 396m)</option>
                        <option value="machowa">Machowa (Krótki Techniczny, 260m)</option>
                    </select>
                </div>
                <button onclick="startSimulation()" class="w-full bg-green-600 hover:bg-green-500 text-white font-bold text-xl py-5 rounded-xl shadow-lg transition-transform transform hover:scale-105">
                    ▶ SYMULUJ BIEG
                </button>
            </div>

            <!-- Parametry Zawodników -->
            <div class="md:col-span-2 bg-slate-800 p-5 rounded-xl border border-slate-700 shadow-lg">
                <h2 class="text-xl font-bold mb-4 border-b border-slate-700 pb-2">Obsada Wyścigu & Sprzęt</h2>
                <div class="space-y-4" id="riders-container"></div>
            </div>
        </div>

        <!-- Widok Symulacji (Ukryty na start) -->
        <div id="sim-view" class="hidden space-y-6">
            <div class="flex justify-between items-center bg-slate-800 p-4 rounded-xl border border-slate-700">
                <div class="text-xl font-bold" id="sim-title">Trwa Wyścig...</div>
                <div class="text-orange-500 font-mono text-xl font-bold" id="sim-time">0.00s</div>
            </div>

            <div class="grid md:grid-cols-2 gap-6">
                <!-- Animacja Canvas -->
                <div class="bg-slate-800 p-4 rounded-xl border border-slate-700 flex justify-center items-center">
                    <canvas id="race-canvas" width="600" height="300" class="w-full h-auto bg-slate-900 rounded-lg shadow-inner border border-slate-700"></canvas>
                </div>
                
                <!-- Log Telemetryczny -->
                <div class="bg-slate-900 p-4 rounded-xl border border-slate-700 h-[330px] overflow-y-auto custom-scrollbar space-y-2 font-mono text-sm" id="event-log">
                    <div class="text-slate-500 italic">Oczekiwanie na start...</div>
                </div>
            </div>
        </div>

        <!-- Wyniki (Ukryte na start) -->
        <div id="results-view" class="hidden space-y-6">
            <div class="bg-slate-800 p-6 rounded-xl border border-slate-700 text-center shadow-lg">
                <h2 class="text-3xl font-bold text-orange-500 mb-2">🏁 META BIEGU</h2>
            </div>
            <div class="grid gap-4" id="results-container"></div>
            <div class="flex justify-center pt-4">
                <button onclick="resetView()" class="bg-slate-700 hover:bg-slate-600 text-white px-8 py-3 rounded-lg font-bold shadow-lg">NOWY BIEG</button>
            </div>
        </div>

    </div>

    <script>
        const TRACK_DATA = {
            'gorzow': { nazwa: "Gorzów (Klasyk)", dlugosc: 329, material: "sjenit", nachylenie_lukow: 2.5, szerokosc: 10.0, ubicie: 60, bronowanie: 40, nawodnienie: 50 },
            'wroclaw': { nazwa: "Wrocław (Głęboka Kopa)", dlugosc: 352, material: "sjenit", nachylenie_lukow: 3.0, szerokosc: 11.5, ubicie: 10, bronowanie: 90, nawodnienie: 70 },
            'krosno': { nazwa: "Krosno (Długi Beton)", dlugosc: 396, material: "granit", nachylenie_lukow: 4.0, szerokosc: 15.0, ubicie: 95, bronowanie: 0, nawodnienie: 30 },
            'machowa': { nazwa: "Machowa (Płaski)", dlugosc: 260, material: "lupek", nachylenie_lukow: 0.0, szerokosc: 9.0, ubicie: 50, bronowanie: 50, nawodnienie: 40 }
        };

        const RIDER_PRESETS = [
            { imie: "B. Zmarzlik", kask: 'A', ref: 96, gaz: 98, bal: 95, zmysl: 96, agr: 95, taktyka: 'late_apex', ztyl: 57, opona: 'Mitas', color: '#ef4444' },
            { imie: "M. Janowski", kask: 'B', ref: 95, gaz: 96, bal: 96, zmysl: 95, agr: 94, taktyka: 'klasyczna', ztyl: 58, opona: 'Mitas', color: '#3b82f6' },
            { imie: "L. Madsen",   kask: 'C', ref: 94, gaz: 95, bal: 94, zmysl: 94, agr: 96, taktyka: 'klasyczna', ztyl: 57, opona: 'Anlas', color: '#f8fafc' },
            { imie: "M. Michelsen",kask: 'D', ref: 95, gaz: 94, bal: 95, zmysl: 93, agr: 95, taktyka: 'late_apex', ztyl: 58, opona: 'Anlas', color: '#eab308' }
        ];

        // Budowanie formularza zawodników
        const container = document.getElementById('riders-container');
        RIDER_PRESETS.forEach((r, i) => {
            container.innerHTML += `
                <div class="flex flex-wrap items-center gap-4 p-4 bg-slate-900 rounded-lg border-l-4 shadow-sm" style="border-left-color: ${r.color}">
                    <div class="w-8 font-bold text-xl text-center" style="color: ${r.color}">${r.kask}</div>
                    <div class="flex-1 min-w-[150px] font-bold text-lg">${r.imie}</div>
                    <div class="flex gap-2 items-center">
                        <span class="text-sm text-slate-400">Tył:</span>
                        <input type="number" id="gear-${i}" value="${r.ztyl}" class="w-16 bg-slate-700 border border-slate-600 p-2 rounded text-center text-white font-mono">
                    </div>
                    <div class="flex gap-2 items-center">
                        <span class="text-sm text-slate-400">Opona:</span>
                        <select id="tire-${i}" class="w-24 bg-slate-700 border border-slate-600 p-2 rounded text-white">
                            <option value="Anlas" ${r.opona=='Anlas'?'selected':''}>Anlas</option>
                            <option value="Mitas" ${r.opona=='Mitas'?'selected':''}>Mitas</option>
                        </select>
                    </div>
                </div>
            `;
        });

        // Logika Animacji i Stanu
        let animFrame;
        let simData = null;
        let currTime = 0.0;
        let maxTime = 0.0;
        let lastTimestamp = 0;
        let shownEvents = new Set();

        async function startSimulation() {
            const trackKey = document.getElementById('track-select').value;
            const tor = TRACK_DATA[trackKey];
            
            const zawodnicy = RIDER_PRESETS.map((r, i) => ({
                imie: r.imie, kask: r.kask,
                refleks: r.ref, gaz: r.gaz, balans: r.bal, zmysl: r.zmysl, agresja: r.agr, taktyka: r.taktyka,
                zebatka_tyl: parseInt(document.getElementById(`gear-${i}`).value),
                opona: document.getElementById(`tire-${i}`).value
            }));

            document.getElementById('setup-view').classList.add('hidden');
            document.getElementById('sim-view').classList.remove('hidden');
            document.getElementById('event-log').innerHTML = '';
            document.getElementById('sim-title').innerText = tor.nazwa;
            shownEvents.clear();
            currTime = 0.0;

            const response = await fetch('/api/simulate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tor, zawodnicy })
            });
            
            simData = await response.json();
            maxTime = Math.max(...simData.wyniki.map(z => z.czas_calkowity)) + 1.0;
            
            lastTimestamp = performance.now();
            animFrame = requestAnimationFrame(animationLoop);
        }

        function animationLoop(timestamp) {
            const dt = (timestamp - lastTimestamp) / 1000.0;
            lastTimestamp = timestamp;
            currTime += dt * 1.5; // Mnożnik prędkości odtwarzania
            
            document.getElementById('sim-time').innerText = currTime.toFixed(2) + 's';
            drawCanvas(currTime);
            updateLog(currTime);

            if (currTime >= maxTime) {
                showResults();
            } else {
                animFrame = requestAnimationFrame(animationLoop);
            }
        }

        function drawCanvas(t) {
            const canvas = document.getElementById('race-canvas');
            const ctx = canvas.getContext('2d');
            
            ctx.fillStyle = '#0f172a'; // bg-slate-950
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            // Tor geometry
            const cxL = 150, cxR = 450, cy = 150, r = 80;
            ctx.strokeStyle = '#334155'; ctx.fillStyle = '#475569'; ctx.lineWidth = 30;
            
            ctx.beginPath();
            ctx.arc(cxL, cy, r, Math.PI / 2, Math.PI * 1.5);
            ctx.lineTo(cxR, cy - r);
            ctx.arc(cxR, cy, r, -Math.PI / 2, Math.PI / 2);
            ctx.lineTo(cxL, cy + r);
            ctx.stroke(); ctx.fill();

            // Start line
            ctx.strokeStyle = 'white'; ctx.lineWidth = 2;
            ctx.beginPath(); ctx.moveTo(300, cy + r - 15); ctx.lineTo(300, cy + r + 15); ctx.stroke();

            if (!simData) return;

            simData.wyniki.forEach(z => {
                const tel = z.telemetria;
                if (tel.length === 0) return;
                let cPt = tel.find(pt => pt.time >= t);
                let pPt = [...tel].reverse().find(pt => pt.time < t) || tel[0];
                if (!cPt) cPt = tel[tel.length - 1];

                let prog = pPt.sector;
                if (cPt.time > pPt.time) {
                    prog = pPt.sector + ((t - pPt.time) / (cPt.time - pPt.time)) * (cPt.sector - pPt.sector);
                }

                if (!z.aktywny && prog >= tel[tel.length-1].sector) return; // Defekt hide

                let lapProg = (prog % 8) / 8.0;
                let baseR = cPt.line === 'banda' ? r + 8 : r - 8;
                let offset = ['A','B','C','D'].indexOf(z.kask) * 3;
                let fR = baseR + offset - 4;
                let x = 0, y = 0;

                if (lapProg < 0.125) { x = 300 + (lapProg/0.125)*150; y = cy + fR; }
                else if (lapProg < 0.375) { let a = Math.PI/2 - ((lapProg-0.125)/0.25)*Math.PI; x = cxR + Math.cos(a)*fR; y = cy + Math.sin(a)*fR; }
                else if (lapProg < 0.625) { x = cxR - ((lapProg-0.375)/0.25)*300; y = cy - fR; }
                else if (lapProg < 0.875) { let a = -Math.PI/2 - ((lapProg-0.625)/0.25)*Math.PI; x = cxL + Math.cos(a)*fR; y = cy + Math.sin(a)*fR; }
                else { x = cxL + ((lapProg-0.875)/0.125)*150; y = cy + fR; }

                const col = RIDER_PRESETS.find(p=>p.kask === z.kask).color;
                ctx.beginPath(); ctx.arc(x, y, 6, 0, 2*Math.PI);
                ctx.fillStyle = col; ctx.fill();
                ctx.strokeStyle = 'black'; ctx.lineWidth=1; ctx.stroke();
                
                ctx.fillStyle = 'white'; ctx.font = '10px sans-serif';
                ctx.fillText(z.imie.split(' ')[1], x+10, y+4);
            });
        }

        function updateLog(t) {
            const logBox = document.getElementById('event-log');
            simData.wydarzenia.forEach((e, idx) => {
                if (e.czas <= t && !shownEvents.has(idx)) {
                    shownEvents.add(idx);
                    let colorCls = 'bg-slate-800 border-slate-600';
                    if (['defekt', 'tasma'].includes(e.typ)) colorCls = 'bg-red-900/40 border-red-500';
                    if (e.typ === 'warn') colorCls = 'bg-yellow-900/40 border-yellow-500 text-yellow-200';
                    
                    logBox.innerHTML += `
                        <div class="p-2 rounded border-l-2 ${colorCls}">
                            <span class="text-slate-400 mr-2">[${e.czas.toFixed(2)}s]</span> ${e.tekst}
                        </div>
                    `;
                    logBox.scrollTop = logBox.scrollHeight;
                }
            });
        }

        function showResults() {
            cancelAnimationFrame(animFrame);
            document.getElementById('sim-view').classList.add('hidden');
            document.getElementById('results-view').classList.remove('hidden');
            
            const cont = document.getElementById('results-container');
            cont.innerHTML = '';
            simData.wyniki.forEach(z => {
                const c = RIDER_PRESETS.find(p=>p.kask === z.kask).color;
                const status = z.aktywny ? `
                    <div class="flex gap-4">
                        <div class="text-center"><div class="text-slate-400 text-xs">Czas</div><div class="font-mono text-green-400 font-bold">${z.czas_calkowity.toFixed(3)}s</div></div>
                        <div class="text-center"><div class="text-slate-400 text-xs">Opona</div><div class="font-mono text-yellow-400 font-bold">${z.motocykl.stan_bieznika.toFixed(0)}%</div></div>
                        <div class="text-center"><div class="text-slate-400 text-xs">Temp</div><div class="font-mono ${z.motocykl.temperatura>100?'text-red-500':'text-orange-400'} font-bold">${z.motocykl.temperatura.toFixed(0)}°C</div></div>
                    </div>
                ` : `<div class="text-red-500 font-bold">WYKLUCZENIE</div>`;

                cont.innerHTML += `
                    <div class="bg-slate-800 p-4 rounded-xl border-l-8 flex justify-between items-center" style="border-left-color: ${c}">
                        <div class="flex items-center space-x-4">
                            <div class="text-2xl font-bold text-slate-500">${z.miejsce}.</div>
                            <div>
                                <div class="text-xl font-bold">${z.imie}</div>
                                <div class="text-sm text-slate-400">Pkt: <span class="text-white font-bold">${z.pkt}</span></div>
                            </div>
                        </div>
                        ${status}
                    </div>
                `;
            });
        }

        function resetView() {
            document.getElementById('results-view').classList.add('hidden');
            document.getElementById('setup-view').classList.remove('hidden');
        }
    </script>
</body>
</html>
"""

# ==========================================
# ENDPOINTY API
# ==========================================

@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

@app.route('/api/simulate', methods=['POST'])
def run_simulation():
    data = request.json
    tor_data = data['tor']
    zawodnicy_data = data['zawodnicy']
    
    wyniki_symulacji = symuluj_wyscig(tor_data, zawodnicy_data)
    return jsonify(wyniki_symulacji)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
