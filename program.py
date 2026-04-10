import random
import time

class Tor:
    def __init__(self, nazwa, dlugosc, nawierzchnia):
        self.nazwa = nazwa
        self.dlugosc = dlugosc
        self.nawierzchnia = nawierzchnia
        self.koleiny = 0.0
        self.przyczepnosc_krawaznik = 1.0 if nawierzchnia == 'kopa' else 0.8
        self.przyczepnosc_banda = 0.6 if nawierzchnia == 'kopa' else 0.5
        
    def aktualizuj_tor(self):
        self.koleiny = min(1.0, self.koleiny + 0.1)
        self.przyczepnosc_krawaznik -= 0.05
        self.przyczepnosc_banda += 0.10

class Motocykl:
    def __init__(self, zebatka_przod, zebatka_tyl, opona):
        self.przelozenie = zebatka_tyl / zebatka_przod
        self.opona = opona
        self.stan_opony = 100.0
        
    def degraduj(self, agresja):
        spadek = 15 if self.opona == 'Anlas' else 10
        self.stan_opony = max(0.0, self.stan_opony - (spadek * (agresja/100)))

class Zawodnik:
    def __init__(self, imie, pole, refleks, gaz, balans, zmysl, agresja, taktyka, motocykl):
        self.imie = imie
        self.pole = pole
        self.refleks = refleks
        self.kontrola_gazu = gaz
        self.balans = balans
        self.zmysl_mechaniczny = zmysl
        self.agresja = agresja
        self.taktyka = taktyka
        self.motocykl = motocykl
        
        self.aktywny = True
        self.powod_wykluczenia = ""
        self.czas_calkowity = 0.0 
        self.czas_okr = 0.0
        self.czas_przed_okr = 0.0

# --- BAZA RÓŻNORODNYCH KOMENTARZY ŻUŻLOWYCH ---
OPISY_START = list((
    "Najlepiej ze startu zabrał się {z_imie}!",
    "Atomowy start! {z_imie} od razu wysuwa się na czoło stawki.",
    "Świetny refleks! {z_imie} zakłada rywali na dojeździe do pierwszego łuku.",
    "Idealnie wstrzelił się w zamek maszyny startowej! {z_imie} z przewagą już na pierwszych metrach."
))

OPISY_TASMA = list((
    "KATASTROFA! {z_imie} wjeżdża w taśmę i zostaje wykluczony!",
    "Ależ błąd! {z_imie} zrywa taśmę! Sędzia nie miał absolutnie żadnych wątpliwości.",
    "Nerwy nie wytrzymały! {z_imie} dotyka taśmy i żegna się z tym biegiem."
))

OPISY_UPADEK = list((
    "❌ KRAKSA! {z_imie} wpadł w głęboką koleinę i leży na torze!",
    "❌ UPADEK! Motocykl podbiło na nierówności, {z_imie} zapoznaje się z nawierzchnią!",
    "❌ GROŹNA SYTUACJA! {z_imie} nie opanował maszyny, uślizg i uderzenie o tor!"
))

OPISY_DEFEKT = list((
    "🔧 DEFEKT! Z motocykla poszedł gęsty dym! {z_imie} kończy jazdę!",
    "🔧 KOSZMAR! Sprzęt odmówił posłuszeństwa, {z_imie} zwalnia na torze.",
    "🔧 Zerwany łańcuch! {z_imie} traci szansę na zdobycie jakichkolwiek punktów w tym biegu."
))

OPISY_OBRONA = list((
    "🛡️ {z_imie} dwoi się i troi, ale {ryw_imie} mądrze zamyka przysłowiowe 'drzwi'!",
    "🛡️ Piękna walka! {z_imie} próbuje atakować, lecz {ryw_imie} jedzie wyśmienicie taktycznie.",
    "🛡️ Fantastyczna defensywa! {ryw_imie} nie zostawia rywalowi ({z_imie}) ani centymetra wolnego miejsca."
))

# --- KOMENTARZE GRUPOWE (BARDZO WIDOWISKOWE) ---
OPISY_POTROJNE = list((
    "🤯 NIEPRAWDOPODOBNE! {z_imie} mija wszystkich trzech rywali ({lista_rywali}) w jednym genialnym ataku! Przechodzi do historii!",
    "🚀 CO ZA SZARŻA! Z ostatniego na pierwsze miejsce! {z_imie} objeżdża całą stawkę ({lista_rywali}) naraz!",
    "🔥 POEZJA SPEEDWAYA! {z_imie} wchodzi między trzech rywali ({lista_rywali}) i zostawia ich daleko w tyle! Akcja sezonu!",
    "👑 CZY ON JEST Z INNEJ PLANETY?! {z_imie} jednym fenomenalnym manewrem wyprzedza całą trójkę ({lista_rywali})!"
))

OPISY_PODWOJNE = list((
    "⚡ PODWÓJNE WYPRZEDZANIE! {z_imie} wciska się i mija dwóch zawodników naraz ({lista_rywali})!",
    "🌪️ DWA PIECZENIE NA JEDNYM OGNIU! {z_imie} niesamowitym napędem objeżdża duet: {lista_rywali}!",
    "🚀 KAPITALNA MIJANKA! {z_imie} bez kompleksów ogrywa dwóch rywali ({lista_rywali}) i przejmuje ich pozycje!",
    "🔥 {z_imie} ma dziś prędkość światła! Wyprzedza {lista_rywali} w jednej, spektakularnej akcji!"
))

# --- KOMENTARZE POJEDYNCZE (1 NA 1) ---
OPISY_WEJSCIE = list((
    "🔥 Pikuje pod łokieć! {z_imie} ostro wchodzi w łuk i mija rywala ({ryw_imie})!",
    "🔥 Brutalny wjazd! {z_imie} wciska się po wewnętrznej i zostawia w tyle zawodnika z przodu ({ryw_imie}).",
    "🔥 Znalazł lukę przy krawężniku! {z_imie} bezbłędnie wyprzedza ({ryw_imie}) na wejściu w wiraż."
))

OPISY_SZCZYT = list((
    "🔥 Krótka piłka na szczycie łuku! {z_imie} znajduje fenomenalną przyczepność i wyprzedza ({ryw_imie}).",
    "🔥 Ależ złamał ten motocykl! {z_imie} ciaśniej na szczycie, a ({ryw_imie}) zostaje w tyle!",
    "🔥 Walka na żyletki! {z_imie} objeżdża rywala ({ryw_imie}) dokładnie w połowie wirażu."
))

OPISY_WYJSCIE_LATE = list((
    "🔥 Klasyczne nożyce! {z_imie} ściął do krawężnika i z potężnym napędem mija ({ryw_imie})!",
    "🔥 Co za manewr! {z_imie} pojechał na opóźniony wierzchołek i dosłownie połknął rywala ({ryw_imie}).",
    "🔥 Prawdziwa inteligencja torowa! {z_imie} przycina do małej i bezlitośnie objeżdża ({ryw_imie}) na wyjściu!"
))

OPISY_WYJSCIE_NORMAL = list((
    "🔥 Zbudował prędkość pod samą bandą! {z_imie} nakrywa rywala ({ryw_imie}) na wyjściu z łuku!",
    "🔥 Złapał idealną przyczepność z odsypanej nawierzchni! {z_imie} wyprzedza ({ryw_imie}) na pełnym gazie.",
    "🔥 Kosmiczna prędkość na wyjściu z wirażu! {z_imie} z łatwością zostawia za plecami ({ryw_imie})."
))

OPISY_PROSTA = list((
    "🔥 Czysta moc 85-konnego silnika! {z_imie} mija rywala ({ryw_imie}) na prostej niczym pendolino!",
    "🔥 Różnica sprzętowa robi swoje! {z_imie} z impetem wyprzedza ({ryw_imie}) pędząc po prostej.",
    "🔥 Ponad 110 km/h i mijanka! {z_imie} po fenomenalnej walce na prostej jest przed rywalem ({ryw_imie})."
))

def komentarz(tekst):
    print(f"   🎙️ {tekst}")
    time.sleep(0.7)

def symuluj_bieg(zawodnicy, tor):
    print(f"\n{'='*50}\nBIEG NA TORZE: {tor.nazwa} ({tor.dlugosc}m)\n{'='*50}")
    
    # --- FAZA 1: START Z MIEJSCA ---
    print("\n📍 PROCEDURA STARTOWA:")
    komentarz("Zawodnicy podjeżdżają pod taśmę... Maszyny na wysokich obrotach!")
    for z in zawodnicy:
        szansa_tasma = 0.05 - (z.refleks * 0.0004)
        if random.random() < szansa_tasma:
            z.aktywny = False
            z.powod_wykluczenia = "Taśma"
            komentarz(random.choice(OPISY_TASMA).format(z_imie=z.imie))
            continue
            
        baza_reakcji = 0.35 
        reakcja = baza_reakcji - (z.refleks * 0.002) + random.uniform(0.0, 0.1)
        bonus_pola = {'A': 0.0, 'B': 0.05, 'C': 0.08, 'D': 0.12} 
        
        z.czas_calkowity = reakcja + bonus_pola[z.pole] 

    aktywni = list(z for z in zawodnicy if z.aktywny)
    aktywni.sort(key=lambda x: x.czas_calkowity) 
    
    komentarz("Taśma w górę! Poszli!")
    if aktywni:
        komentarz(random.choice(OPISY_START).format(z_imie=aktywni.imie))

    # --- DYSTANS: 4 OKRĄŻENIA W PODZIALE NA SEKTORY ---
    for okr in range(1, 5):
        if len(list(z for z in aktywni if z.aktywny)) == 0: break
        print(f"\n{'-'*18} OKRĄŻENIE {okr} {'-'*18}")
        
        for z in aktywni:
            z.czas_przed_okr = z.czas_calkowity if okr > 1 else 0.0
            
        kolejnosc_w_sektorze = list(z.imie for z in aktywni)
        
        nazwa_prostej = "Dojazd do 1. łuku" if okr == 1 else "Prosta startowa"
        
        sektory = tuple((
            tuple((nazwa_prostej, "prosta")),
            tuple(("Wejście w 1. łuk", "wejscie")),
            tuple(("Szczyt 1. łuku", "szczyt")),
            tuple(("Wyjście z 1. łuku", "wyjscie")),
            tuple(("Przeciwległa prosta", "prosta")),
            tuple(("Wejście w 2. łuk", "wejscie")),
            tuple(("Szczyt 2. łuku", "szczyt")),
            tuple(("Wyjście z 2. łuku", "wyjscie"))
        ))
        
        baza_sektora = (tor.dlugosc / 8.0) / 22.0 
        
        for sektor_nazwa, sektor_typ in sektory:
            akcje_w_sektorze = list()
            
            for z in aktywni:
                if not z.aktywny: continue
                
                if sektor_typ == "wejscie" and random.random() < (0.002 + tor.koleiny * 0.01 - z.balans * 0.00005):
                    z.aktywny = False
                    z.powod_wykluczenia = "Upadek"
                    akcje_w_sektorze.append(random.choice(OPISY_UPADEK).format(z_imie=z.imie))
                    continue
                if sektor_typ == "prosta" and random.random() < 0.001:
                    z.aktywny = False
                    z.powod_wykluczenia = "Defekt"
                    akcje_w_sektorze.append(random.choice(OPISY_DEFEKT).format(z_imie=z.imie))
                    continue
                    
                wsp_przyczepnosci = tor.przyczepnosc_banda if z.zmysl_mechaniczny > 70 else tor.przyczepnosc_krawaznik
                bonus_opony = 1.05 if z.motocykl.opona == 'Anlas' and z.motocykl.stan_opony > 50 else 1.0
                
                zysk = 0.0
                if sektor_typ == "prosta":
                    zysk = (z.motocykl.przelozenie * 0.015) + (z.kontrola_gazu * 0.002)
                elif sektor_typ == "wejscie":
                    zysk = (z.balans * 0.003)
                elif sektor_typ == "szczyt":
                    zysk = (z.balans * 0.002) * wsp_przyczepnosci
                elif sektor_typ == "wyjscie":
                    if z.taktyka == 'late_apex':
                        zysk = (z.kontrola_gazu * 0.004) * wsp_przyczepnosci * bonus_opony
                    else:
                        zysk = (z.kontrola_gazu * 0.0025) * wsp_przyczepnosci * bonus_opony
                        
                czas_sektora = baza_sektora - zysk + random.uniform(0.01, 0.06)
                z.czas_calkowity += czas_sektora
                z.motocykl.degraduj(z.agresja / 8.0)
            
            aktywni = list(z for z in aktywni if z.aktywny)
            if not aktywni: break
            aktywni.sort(key=lambda x: x.czas_calkowity)
            
            atakowali = set()
            for i in range(1, len(aktywni)):
                z = aktywni[i]
                rywal = aktywni[i-1]
                strata = z.czas_calkowity - rywal.czas_calkowity
                
                if strata < 0.15 and z.imie not in atakowali:
                    atakowali.add(z.imie)
                    if z.agresja + random.randint(0, 40) > rywal.agresja + random.randint(0, 40):
                        z.czas_calkowity = rywal.czas_calkowity - 0.02
                    else:
                        if random.random() < 0.08:
                            akcje_w_sektorze.append(random.choice(OPISY_OBRONA).format(z_imie=z.imie, ryw_imie=rywal.imie))
            
            aktywni.sort(key=lambda x: x.czas_calkowity)
            nowa_kolejnosc = list(z.imie for z in aktywni)
            
            # --- ZAAWANSOWANA LOGIKA WYKRYWANIA GRUPOWYCH WYPRZEDZEŃ ---
            for imie in nowa_kolejnosc:
                if imie not in kolejnosc_w_sektorze: continue
                
                idx_new = nowa_kolejnosc.index(imie)
                idx_old = kolejnosc_w_sektorze.index(imie)
                
                if idx_new < idx_old:
                    z_obj = next(zaw for zaw in aktywni if zaw.imie == imie)
                    pokonani = list()
                    
                    for ryw_imie in kolejnosc_w_sektorze:
                        if ryw_imie == imie: continue
                        if ryw_imie not in nowa_kolejnosc: continue
                        
                        ryw_idx_old = kolejnosc_w_sektorze.index(ryw_imie)
                        ryw_idx_new = nowa_kolejnosc.index(ryw_imie)
                        
                        if idx_old > ryw_idx_old and idx_new < ryw_idx_new:
                            pokonani.append(ryw_imie)
                    
                    # Różnicowanie komentarzy w zależności od ilości wyprzedzonych rywali
                    if len(pokonani) == 3:
                        format_rywali = ", ".join(pokonani)
                        akcje_w_sektorze.append(random.choice(OPISY_POTROJNE).format(z_imie=z_obj.imie, lista_rywali=format_rywali))
                    elif len(pokonani) == 2:
                        format_rywali = " i ".join(pokonani)
                        akcje_w_sektorze.append(random.choice(OPISY_PODWOJNE).format(z_imie=z_obj.imie, lista_rywali=format_rywali))
                    elif len(pokonani) == 1:
                        ryw_imie_solo = pokonani
                        if sektor_typ == "wyjscie" and z_obj.taktyka == "late_apex":
                            akcje_w_sektorze.append(random.choice(OPISY_WYJSCIE_LATE).format(z_imie=z_obj.imie, ryw_imie=ryw_imie_solo))
                        elif sektor_typ == "wyjscie":
                            akcje_w_sektorze.append(random.choice(OPISY_WYJSCIE_NORMAL).format(z_imie=z_obj.imie, ryw_imie=ryw_imie_solo))
                        elif sektor_typ == "wejscie":
                            akcje_w_sektorze.append(random.choice(OPISY_WEJSCIE).format(z_imie=z_obj.imie, ryw_imie=ryw_imie_solo))
                        elif sektor_typ == "prosta":
                            akcje_w_sektorze.append(random.choice(OPISY_PROSTA).format(z_imie=z_obj.imie, ryw_imie=ryw_imie_solo))
                        else:
                            akcje_w_sektorze.append(random.choice(OPISY_SZCZYT).format(z_imie=z_obj.imie, ryw_imie=ryw_imie_solo))
                                
            kolejnosc_w_sektorze = list(nowa_kolejnosc)
            
            if akcje_w_sektorze:
                print(f"\n📍 {sektor_nazwa.upper()}:")
                for akcja in akcje_w_sektorze:
                    komentarz(akcja)
            
        tor.aktualizuj_tor()
        
        if aktywni:
            for z in aktywni:
                z.czas_okr = z.czas_calkowity - z.czas_przed_okr
                
            print(f"\n🏁 KONIEC OKRĄŻENIA {okr} 🏁")
            lider_czas = aktywni.czas_calkowity
            for pos, z in enumerate(aktywni):
                strata_str = "" if pos == 0 else f" (+{(z.czas_calkowity - lider_czas):.3f}s)"
                print(f"   {pos+1}. {z.imie} | Czas okrążenia: {z.czas_okr:.3f}s | Czas całkowity: {z.czas_calkowity:.3f}s{strata_str}")
            print("")

    # --- WYNIKI KOŃCOWE ---
    print(f"\n{'='*50}\nMETA BIEGU\n{'='*50}")
    punkty_tab = tuple((3, 2, 1, 0))
    
    for i, z in enumerate(aktywni):
        pkt = punkty_tab[i] if i < len(punkty_tab) else 0
        print(f"{i+1}. {z.imie} | Czas łączny: {z.czas_calkowity:.3f}s | Pkt: {pkt}")
        
    for z in zawodnicy:
        if not z.aktywny:
            print(f"-. {z.imie} | Wykluczenie: {z.powod_wykluczenia} | Pkt: 0")

if __name__ == "__main__":
    tor = Tor(nazwa="Stadion im. E. Jancarza", dlugosc=329, nawierzchnia="beton")
    
    z1 = Zawodnik("B. Zmarzlik", 'A', refleks=95, gaz=98, balans=95, zmysl=90, agresja=95, taktyka='late_apex', motocykl=Motocykl(20, 41, 'Anlas'))
    z2 = Zawodnik("M. Janowski", 'B', refleks=85, gaz=90, balans=92, zmysl=85, agresja=80, taktyka='klasyczna', motocykl=Motocykl(20, 42, 'Mitas'))
    z3 = Zawodnik("L. Madsen",   'C', refleks=88, gaz=85, balans=88, zmysl=80, agresja=85, taktyka='klasyczna', motocykl=Motocykl(21, 44, 'Mitas'))
    z4 = Zawodnik("M. Michelsen",'D', refleks=90, gaz=88, balans=85, zmysl=85, agresja=88, taktyka='late_apex', motocykl=Motocykl(21, 43, 'Anlas'))
    
    lista_zawodnikow = list((z1, z2, z3, z4))
    symuluj_bieg(lista_zawodnikow, tor)
