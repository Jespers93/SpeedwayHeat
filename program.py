from flask import Flask, request, jsonify, render_template_string
import random

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

    # PROCEDURA STARTOWA
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
        
        # Na starcie wszyscy jadą przy krawężniku by dojechać do łuku
        z.telemetria.append({"sector": 0, "time": z.czas_calkowity, "line": "krawaznik"})

    aktywni = [z for z in zawodnicy if z.aktywny]
    aktywni.sort(key=lambda x: x.czas_calkowity) 
    if aktywni:
        dodaj_wydarzenie("start", aktywni[0].czas_calkowity, random.choice(OPISY["START"]).replace("{z}", aktywni[0].imie))

    globalny_sektor = 0
    sektory = ["prosta", "wejscie", "szczyt", "wyjscie"] * 2
    baza_sektora = (tor.dlugosc / 8.0) / 23.5 

    # DYSTANS (4 okrążenia)
    for okr in range(1, 5):
        if not aktywni: break
        
        for sektor_typ in sektory:
            globalny_sektor += 1
            for z in aktywni:
                if not z.aktywny: continue
                
                # Losowe Defekty
                if sektor_typ == "prosta" and random.random() < 0.0003:
                    z.aktywny = False
                    z.powod_wykluczenia = "Defekt"
                    dodaj_wydarzenie("defekt", z.czas_calkowity, OPISY["DEFEKT"][0].replace("{z}", z.imie))
                    continue

                # --- ZAAWANSOWANE ZMIANY ŚCIEŻEK JAZDY ---
                stara_linia = z.wybrana_linia
                
                # 1. Zmysł mechaniczny szuka przyczepności na torze
                if z.zmysl_mechaniczny > random.randint(40, 90):
                    if tor.przyczepnosc_banda > tor.przyczepnosc_krawaznik + 0.05:
                        z.wybrana_linia = 'banda'
                    elif tor.przyczepnosc_krawaznik > tor.przyczepnosc_banda + 0.05:
                        z.wybrana_linia = 'krawaznik'
                    else:
                        # 2. Jeśli przyczepność jest równa, decyduje taktyka i geometria
                        if sektor_typ == "wyjscie" and z.taktyka == 'klasyczna':
                            z.wybrana_linia = 'banda' # Wypuszcza pod płot na wyjściu
                        elif sektor_typ == "szczyt" and z.taktyka == 'late_apex':
                            z.wybrana_linia = 'krawaznik' # Ścina do krawężnika na szczycie (Nożyce)
                        elif sektor_typ == "wejscie" and z.taktyka == 'late_apex':
                            z.wybrana_linia = 'banda' # Robi miejsce szeroko na wejściu

                # 3. Omijanie szprycy (Walka w kontakcie)
                idx_z = aktywni.index(z)
                if idx_z > 0:
                    rywal_przed = aktywni[idx_z - 1]
                    # Jeśli jest tuż za rywalem, mądry zawodnik ucieka z jego ścieżki
                    if z.czas_calkowity - rywal_przed.czas_calkowity < 0.15 and z.zmysl_mechaniczny > 75:
                        z.wybrana_linia = 'banda' if rywal_przed.wybrana_linia == 'krawaznik' else 'krawaznik'

                # Generowanie komentarza o zmianie linii (żeby nie zaspamować logów - tylko 6% szans na log)
                if stara_linia != z.wybrana_linia and random.random() < 0.06:
                    if z.wybrana_linia == 'banda':
                        dodaj_wydarzenie("info", z.czas_calkowity, f"🔄 {z.imie} wynosi się na zewnętrzną szukając napędu.")
                    else:
                        dodaj_wydarzenie("info", z.czas_calkowity, f"🔄 {z.imie} ścina do krawężnika, uciekając z odsypu!")

                # --- KINEMATYKA I OBLICZANIE CZASU ---
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
                    if z.motocykl.stan_bieznika < 25 and random.random() < 0.05:
                         dodaj_wydarzenie("warn", z.czas_calkowity, f"⚠️ Opona u {z.imie} całkowicie starta! Ślizga się!")
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
                
                # Rejestrowanie telemetrii dla interfejsu (w tym linia jazdy do animacji promienia)
                z.telemetria.append({"sector": globalny_sektor, "time": z.czas_calkowity, "line": z.wybrana_linia})

            aktywni = [z for z in aktywni if z.aktywny]
            aktywni.sort(key=lambda x: x.czas_calkowity)
            
            # Walka i Wyprzedzanie
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
                            if random.random() < 0.2:
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
# INTERFEJS WEBOWY (HTML/JS/TAILWIND)
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
<body class="bg-slate-900 text-slate-200 font-sans min-h-screen pb-12">
    <div class="max-w-6xl mx-auto p-4 md:p-6 space-y-6">
        
        <!-- Header -->
        <div class="flex items-center justify-between bg-slate-800 p-4 md:p-5 rounded-xl border border-slate-700 shadow-xl">
            <div class="flex items-center space-x-4">
                <div class="w-12 h-12 bg-orange-600 rounded-full flex items-center justify-center font-bold text-2xl shadow-lg">Ż</div>
                <h1 class="text-2xl md:text-3xl font-bold tracking-wider">SYMULATOR <span class="text-orange-500">PRO</span></h1>
            </div>
            <div class="text-slate-400 font-mono text-xs md:text-sm text-right">Silnik: Python Flask<br>Render: HTML5 Canvas</div>
        </div>

        <!-- EKRAN KONFIGURACJI -->
        <div id="setup-view" class="grid md:grid-cols-3 gap-6">
            
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
                <button onclick="startSimulation()" class="w-full bg-green-600 hover:bg-green-500 text-white font-bold text-xl py-5 rounded-xl shadow-lg transition-transform transform hover:scale-105 border-b-4 border-green-800">
                    ▶ SYMULUJ BIEG
                </button>
            </div>

            <div class="md:col-span-2 bg-slate-800 p-5 rounded-xl border border-slate-700 shadow-lg">
                <h2 class="text-xl font-bold mb-4 border-b border-slate-700 pb-2">Obsada Wyścigu & Sprzęt</h2>
                <div class="space-y-4" id="riders-container"></div>
            </div>
        </div>

        <!-- EKRAN SYMULACJI (Powiększony Canvas) -->
        <div id="sim-view" class="hidden space-y-6">
            
            <div class="flex justify-between items-center bg-slate-800 p-4 rounded-xl border border-slate-700 shadow-lg">
                <div>
                    <div class="text-xs text-slate-400 uppercase tracking-widest">Trwa wyścig</div>
                    <div class="text-xl font-bold" id="sim-title">---</div>
                </div>
                <div class="text-right">
                    <div class="text-xs text-slate-400 uppercase tracking-widest">Czas</div>
                    <div class="text-orange-500 font-mono text-2xl font-bold" id="sim-time">0.00s</div>
                </div>
            </div>

            <!-- POTĘŻNY CANVAS ANIMACJI -->
            <div class="bg-slate-800 p-4 rounded-xl border border-slate-700 shadow-xl overflow-hidden flex justify-center w-full">
                <!-- Rozdzielczość wewnętrzna 1000x400 (będzie skalowana przez CSS w razie potrzeby) -->
                <canvas id="race-canvas" width="1000" height="400" class="w-full max-w-full h-auto bg-slate-900 rounded-lg shadow-inner border border-slate-700"></canvas>
            </div>
            
            <!-- LOG TELEMETRYCZNY -->
            <div class="bg-slate-900 p-4 rounded-xl border border-slate-700 h-[250px] overflow-y-auto custom-scrollbar space-y-2 font-mono text-sm shadow-inner" id="event-log">
                <div class="text-slate-500 italic">Oczekiwanie na zapalenie zielonego światła...</div>
            </div>

        </div>

        <!-- EKRAN WYNIKÓW -->
        <div id="results-view" class="hidden space-y-6">
            <div class="bg-slate-800 p-6 rounded-xl border border-slate-700 text-center shadow-lg">
                <h2 class="text-4xl font-bold text-orange-500 mb-2">🏁 META BIEGU</h2>
                <p class="text-slate-400 text-lg" id="res-title">---</p>
            </div>
            <div class="grid gap-4" id="results-container"></div>
            <div class="flex justify-center pt-6">
                <button onclick="resetView()" class="bg-slate-700 hover:bg-slate-600 text-white px-10 py-4 rounded-xl font-bold text-lg shadow-lg border-b-4 border-slate-900 transition-colors">
                    NOWY BIEG
                </button>
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

        const container = document.getElementById('riders-container');
        RIDER_PRESETS.forEach((r, i) => {
            container.innerHTML += `
                <div class="flex flex-wrap items-center justify-between gap-4 p-4 bg-slate-900 rounded-lg border-l-4 shadow-sm" style="border-left-color: ${r.color}">
                    <div class="flex items-center gap-4">
                        <div class="w-8 h-8 rounded flex items-center justify-center font-bold text-slate-900" style="background-color: ${r.color}">${r.kask}</div>
                        <div class="font-bold text-lg w-32">${r.imie}</div>
                    </div>
                    <div class="flex flex-wrap items-center gap-4">
                        <div class="flex flex-col">
                            <span class="text-xs text-slate-400 uppercase">Zębatka tył</span>
                            <input type="number" id="gear-${i}" value="${r.ztyl}" min="50" max="65" class="w-16 bg-slate-700 border border-slate-600 p-2 rounded text-center text-white font-mono">
                        </div>
                        <div class="flex flex-col">
                            <span class="text-xs text-slate-400 uppercase">Opona</span>
                            <select id="tire-${i}" class="w-24 bg-slate-700 border border-slate-600 p-2 rounded text-white font-mono">
                                <option value="Anlas" ${r.opona=='Anlas'?'selected':''}>Anlas</option>
                                <option value="Mitas" ${r.opona=='Mitas'?'selected':''}>Mitas</option>
                            </select>
                        </div>
                    </div>
                </div>
            `;
        });

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
            maxTime = Math.max(...simData.wyniki.map(z => z.czas_calkowity)) + 1.5;
            
            lastTimestamp = performance.now();
            animFrame = requestAnimationFrame(animationLoop);
        }

        function animationLoop(timestamp) {
            const dt = (timestamp - lastTimestamp) / 1000.0;
            lastTimestamp = timestamp;
            currTime += dt * 1.5; 
            
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
            
            // Wymiary z atrybutów width/height
            const W = canvas.width;
            const H = canvas.height;
            
            ctx.fillStyle = '#0f172a'; // bg-slate-950
            ctx.fillRect(0, 0, W, H);
            
            // Geometria ogromnego owalu
            const r = 130; // Bazowy promień łuku
            const cxL = 250; // Lewy środek
            const cxR = W - 250; // Prawy środek
            const cy = H / 2; // Środek pionowy (200)

            // Rysowanie trawy wewnątrz i na zewnątrz
            ctx.fillStyle = '#1e293b'; ctx.fillRect(0,0,W,H);
            
            // Rysowanie toru (gruba szara linia jako nawierzchnia)
            ctx.strokeStyle = '#475569'; 
            ctx.lineWidth = 80;
            ctx.lineCap = 'butt';
            
            ctx.beginPath();
            ctx.arc(cxL, cy, r, Math.PI / 2, Math.PI * 1.5);
            ctx.lineTo(cxR, cy - r);
            ctx.arc(cxR, cy, r, -Math.PI / 2, Math.PI / 2);
            ctx.lineTo(cxL, cy + r);
            ctx.stroke();

            // Rysowanie obrysów (krawężnik i banda)
            ctx.strokeStyle = '#94a3b8'; ctx.lineWidth = 2;
            ctx.beginPath(); ctx.arc(cxL, cy, r-40, Math.PI/2, Math.PI*1.5); ctx.lineTo(cxR, cy-r+40); ctx.arc(cxR, cy, r-40, -Math.PI/2, Math.PI/2); ctx.lineTo(cxL, cy+r-40); ctx.stroke();
            ctx.beginPath(); ctx.arc(cxL, cy, r+40, Math.PI/2, Math.PI*1.5); ctx.lineTo(cxR, cy-r-40); ctx.arc(cxR, cy, r+40, -Math.PI/2, Math.PI/2); ctx.lineTo(cxL, cy+r+40); ctx.stroke();


            // Linia startu/mety
            ctx.strokeStyle = 'white'; ctx.lineWidth = 4;
            ctx.beginPath(); ctx.moveTo(cxL + 150, cy + r - 40); ctx.lineTo(cxL + 150, cy + r + 40); ctx.stroke();

            if (!simData) return;

            simData.wyniki.forEach(z => {
                const tel = z.telemetria;
                if (tel.length === 0) return;
                let cPt = tel.find(pt => pt.time >= t);
                let pPt = [...tel].reverse().find(pt => pt.time < t) || tel[0];
                if (!cPt) cPt = tel[tel.length - 1];

                let prog = pPt.sector;
                let ratio = 0;
                if (cPt.time > pPt.time) {
                    ratio = (t - pPt.time) / (cPt.time - pPt.time);
                    prog = pPt.sector + ratio * (cPt.sector - pPt.sector);
                }

                if (!z.aktywny && prog >= tel[tel.length-1].sector) return; // Defekt

                // --- PŁYNNA INTERPOLACJA LINII JAZDY ---
                // Linia krawężnika to r - 15, linia bandy to r + 15
                let rPrev = pPt.line === 'banda' ? r + 15 : r - 15;
                let rNext = cPt.line === 'banda' ? r + 15 : r - 15;
                
                let currentR = rPrev + (rNext - rPrev) * ratio;

                // Rozsunięcie kasków, żeby się nie nakładały idealnie 
                let offset = ['A','B','C','D'].indexOf(z.kask) * 6;
                let finalR = currentR + offset - 9; // Środek dla całego zgrupowania

                let lapProg = (prog % 8) / 8.0;
                let x = 0, y = 0;

                // Odwzorowanie na powiększony owal
                if (lapProg < 0.125) { 
                    x = (cxL + 150) + (lapProg/0.125)*(cxR - cxL - 150); 
                    y = cy + finalR; 
                }
                else if (lapProg < 0.375) { 
                    let a = Math.PI/2 - ((lapProg-0.125)/0.25)*Math.PI; 
                    x = cxR + Math.cos(a)*finalR; 
                    y = cy + Math.sin(a)*finalR; 
                }
                else if (lapProg < 0.625) { 
                    x = cxR - ((lapProg-0.375)/0.25)*(cxR - cxL); 
                    y = cy - finalR; 
                }
                else if (lapProg < 0.875) { 
                    let a = -Math.PI/2 - ((lapProg-0.625)/0.25)*Math.PI; 
                    x = cxL + Math.cos(a)*finalR; 
                    y = cy + Math.sin(a)*finalR; 
                }
                else { 
                    x = cxL + ((lapProg-0.875)/0.125)*150; 
                    y = cy + finalR; 
                }

                const col = RIDER_PRESETS.find(p=>p.kask === z.kask).color;
                
                // Rysowanie Kasku
                ctx.beginPath(); ctx.arc(x, y, 9, 0, 2*Math.PI);
                ctx.fillStyle = col; ctx.fill();
                ctx.strokeStyle = '#ffffff'; ctx.lineWidth=2; ctx.stroke();
                
                // Imię obok
                ctx.fillStyle = '#cbd5e1'; ctx.font = 'bold 12px sans-serif';
                ctx.fillText(z.imie.split(' ')[1], x+15, y+5);
            });
        }

        function updateLog(t) {
            const logBox = document.getElementById('event-log');
            simData.wydarzenia.forEach((e, idx) => {
                if (e.czas <= t && !shownEvents.has(idx)) {
                    shownEvents.add(idx);
                    let colorCls = 'bg-slate-800 border-slate-600 text-slate-300';
                    
                    if (['defekt', 'tasma'].includes(e.typ)) colorCls = 'bg-red-900/40 border-red-500 text-white font-bold';
                    if (e.typ === 'warn') colorCls = 'bg-yellow-900/30 border-yellow-600 text-yellow-300';
                    if (e.typ === 'info') colorCls = 'bg-blue-900/20 border-blue-600 text-blue-300 italic';
                    if (e.typ === 'atak') colorCls = 'bg-orange-900/20 border-orange-500 text-orange-200 font-bold';
                    
                    logBox.innerHTML += `
                        <div class="p-3 rounded-lg border-l-4 ${colorCls} shadow-sm">
                            <span class="text-slate-500 mr-2 font-mono">[${e.czas.toFixed(2)}s]</span> ${e.tekst}
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
            document.getElementById('res-title').innerText = document.getElementById('sim-title').innerText;
            
            const cont = document.getElementById('results-container');
            cont.innerHTML = '';
            simData.wyniki.forEach(z => {
                const c = RIDER_PRESETS.find(p=>p.kask === z.kask).color;
                const status = z.aktywny ? `
                    <div class="flex flex-wrap gap-4 mt-4 md:mt-0 w-full md:w-auto bg-slate-900 p-3 rounded-lg border border-slate-700">
                        <div class="text-center px-3 border-r border-slate-700 last:border-0"><div class="text-slate-400 text-xs uppercase">Czas</div><div class="font-mono text-green-400 text-lg font-bold">${z.czas_calkowity.toFixed(3)}s</div></div>
                        <div class="text-center px-3 border-r border-slate-700 last:border-0"><div class="text-slate-400 text-xs uppercase">Opona</div><div class="font-mono text-yellow-400 text-lg font-bold">${z.motocykl.stan_bieznika.toFixed(0)}%</div></div>
                        <div class="text-center px-3 border-r border-slate-700 last:border-0"><div class="text-slate-400 text-xs uppercase">Temp</div><div class="font-mono ${z.motocykl.temperatura>100?'text-red-500':'text-orange-400'} text-lg font-bold">${z.motocykl.temperatura.toFixed(0)}°C</div></div>
                        <div class="text-center px-3 border-r border-slate-700 last:border-0"><div class="text-slate-400 text-xs uppercase">Energia</div><div class="font-mono text-blue-400 text-lg font-bold">${z.stamina.toFixed(0)}</div></div>
                    </div>
                ` : `<div class="text-red-500 font-bold tracking-widest bg-red-900/20 px-6 py-3 rounded-lg border border-red-800">WYKLUCZENIE (${z.powod_wykluczenia.toUpperCase()})</div>`;

                cont.innerHTML += `
                    <div class="bg-slate-800 p-5 rounded-xl border-l-8 shadow-md flex flex-col md:flex-row justify-between items-start md:items-center transition-all hover:bg-slate-750" style="border-left-color: ${c}">
                        <div class="flex items-center space-x-5">
                            <div class="text-3xl font-black text-slate-600">${z.miejsce}.</div>
                            <div>
                                <div class="text-2xl font-bold text-white">${z.imie}</div>
                                <div class="text-sm text-slate-400">Pole <span style="color:${c}" class="font-bold">${z.kask}</span> | Pkt: <span class="text-white font-bold text-lg">${z.pkt}</span></div>
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
    # Uruchomienie lokalnego serwera na porcie 5000
    app.run(debug=True, port=5000)
