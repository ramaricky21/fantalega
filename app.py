from flask import session
import sqlite3
from flask import Flask, render_template, request, redirect
import pandas as pd
app = Flask(__name__)

app.secret_key = "fantalega123"

# giocatori (base iniziale)
players = [
    {"nome": "Vlahovic", "ruolo": "ATT"},
    {"nome": "Lautaro", "ruolo": "ATT"},
    {"nome": "Leao", "ruolo": "ATT"},
    {"nome": "Barella", "ruolo": "CEN"},
    {"nome": "Tonali", "ruolo": "CEN"},
    {"nome": "Di Lorenzo", "ruolo": "DIF"},
    {"nome": "Bastoni", "ruolo": "DIF"},
    {"nome": "Donnarumma", "ruolo": "POR"},
    {"nome": "Sias", "ruolo": "ATT"},
    {"nome": "Feiap", "ruolo": "ATT"},
    {"nome": "Geuwp", "ruolo": "ATT"},
    {"nome": "Eqeufh", "ruolo": "CEN"},
    {"nome": "SWGiewq", "ruolo": "CEN"},
    {"nome": "Di Fa", "ruolo": "DIF"},
    {"nome": "Ruf", "ruolo": "DIF"},
    {"nome": "Afaq", "ruolo": "POR"},
    {"nome": "Vlahoegvic", "ruolo": "ATT"},
    {"nome": "Lautagwsrgro", "ruolo": "ATT"},
    {"nome": "Learwo", "ruolo": "ATT"},
    {"nome": "BarsaGella", "ruolo": "DIF"},
    {"nome": "Tonahtdli", "ruolo": "CEN"},
    {"nome": "Dtri Lsghorenzo", "ruolo": "DIF"},
    {"nome": "Bastdhtroni", "ruolo": "DIF"},
    {"nome": "Donrehyrarumma", "ruolo": "POR"},
    {"nome": "BarGella", "ruolo": "DIF"},
    {"nome": "Tonhtdli", "ruolo": "CEN"},
    {"nome": "Dtri Lsghorenzo", "ruolo": "DIF"},
    {"nome": "Bastroni", "ruolo": "DIF"},
    {"nome": "Donrhyrarumma", "ruolo": "POR"}
]

BONUS_MALUS = {
    "gol segnato": 3,
    "assist": 1,
    "ammonizione": -0.5,
    "espulsione": -1,
    "rigore parato": 3,
    "rigore sbagliato": -3,
    "rigore segnato": 3,
    "autogoal": -3,
    "goal subito": -1,  #per i portieri
    "porta inviolata": 1,  #per portieri
    "player of the match": 0.5,
    
}


MODULI = [
    {"DIF": 3, "CEN": 4, "ATT": 3},
    {"DIF": 4, "CEN": 3, "ATT": 3},
    {"DIF": 3, "CEN": 5, "ATT": 2},
    {"DIF": 4, "CEN": 5, "ATT": 1},
    {"DIF": 4, "CEN": 4, "ATT": 2},
    {"DIF": 5, "CEN": 3, "ATT": 2},
    {"DIF": 5, "CEN": 4, "ATT": 1}
]




squadre = {}

formazione = {
    "titolari": [
        {"nome": "...", "ruolo": "...", "voto": 6},
    ],
    "panchina": [
        {"nome": "...", "ruolo": "...", "ordine": 1},
    ]
}


def init_classifica_da_db():
    conn = sqlite3.connect("fantalega.db")
    c = conn.cursor()

    c.execute("SELECT squadra FROM utenti WHERE role != 'admin'")
    rows = c.fetchall()

    conn.close()

    for (squadra,) in rows:
        if squadra:
            crea_squadra_classifica(squadra)

def ensure_squadra(nome):
    if nome not in squadre:
        squadre[nome] = {
            "titolari": [],
            "panchina": [],
            "rosa": []
        }


classifica = {}
def crea_squadra_classifica(nome):
    if nome not in classifica:
        classifica[nome] = {
            "pt": 0,
            "v": 0,
            "p": 0,
            "s": 0,
            "giocate": 0,
            "gf": 0,
            "gs": 0,
            "pf": 0
        }
        
        

giornate=[]
giornata_corrente = 1
giornata = giornata_corrente

def classifica_ordinata():
    # assicura che tutte le squadre utenti siano dentro classifica
    conn = sqlite3.connect("fantalega.db")
    c = conn.cursor()

    c.execute("SELECT squadra FROM utenti WHERE role != 'admin'")
    squadre_db = [x[0] for x in c.fetchall()]

    conn.close()

    for s in squadre_db:
        if s not in classifica:
            crea_squadra_classifica(s)

    return sorted(
        classifica.items(),
        key=lambda x: (
            x[1].get("pt", 0),
            x[1].get("pf", 0)
        ),
        reverse=True
    )

def calcola_punteggio(voto, eventi):
    totale = voto

    for evento, valore in BONUS_MALUS.items():
        totale += eventi.get(evento, 0) * valore

    return totale


def prendi_voto_eventi(nome, ruolo, giornata):
    conn = sqlite3.connect("fantalega.db")
    c = conn.cursor()

    c.execute("""
        SELECT voto, gol, assist, ammonizione, espulsione,
            rigore_parato, rigore_sbagliato, rigore_segnato,
            autogoal, goal_subito, porta_inviolata, player_of_the_match
        FROM voti_giornata
        WHERE nome = ? AND giornata = ?
    """, (nome, giornata))

    res = c.fetchone()
    conn.close()

    if not res:
        return 0, {}   # 0 = non ha giocato

    (voto, gol, assist, amm, esp,
     rig_par, rig_sba, rig_seg,
     autogoal, gs, pi, potm) = res

    eventi = {
        "gol segnato": gol,
        "assist": assist,
        "ammonizione": amm,
        "espulsione": esp,
        "rigore parato": rig_par,
        "rigore sbagliato": rig_sba,
        "rigore segnato": rig_seg,
        "autogoal": autogoal,
        "goal subito": gs,
        "porta inviolata": pi,
        "player of the match": potm
    }
    
    # porta inviolata automatica
    if ruolo == "POR" and gs == 0:
        eventi["porta inviolata"] = 1
    
    return voto, eventi


def valida_rosa(squadra):
    return len(squadra["rosa"]) == 25


def valida_squadra(squadra):
    if not isinstance(squadra, dict):
        return False

    if "titolari" not in squadra or "panchina" not in squadra:
        return False

    if len(squadra["titolari"]) < 11:
        return False

    if len(squadra["panchina"]) < 0:
        return False

    return True



def prepara_formazione(squadra):
    titolari = squadra["titolari"][:]
    panchina = squadra["panchina"][:]
    return titolari, panchina


def valida_modulo(squadra):
    ruoli = {"DIF": 0, "CEN": 0, "ATT": 0, "POR": 0}

    for g in squadra:
        ruoli[g["ruolo"]] += 1

    return ruoli


def trova_modulo(ruoli):
    for m in MODULI:
        if (
            ruoli["DIF"] >= m["DIF"] and
            ruoli["CEN"] >= m["CEN"] and
            ruoli["ATT"] >= m["ATT"]
        ):
            return m
    return None


def sostituzioni(titolari, panchina):

    final = []
    panchina = panchina[:]  # copia

    for g in titolari:

        # se ha voto ok
        if g["voto"] > 0:
            final.append(g)
            continue

        sostituto = None

        # 🧤 CASO PORTIERE: SOLO PORTIERI, NIENTE FALLBACK
        if g["ruolo"] == "POR":

            for p in panchina:
                if p["ruolo"] == "POR" and p["voto"] > 0:
                    sostituto = p
                    break

        else:
            # 1. stesso ruolo (ordine panchina)
            for p in panchina:
                if p["ruolo"] == g["ruolo"] and p["voto"] > 0:
                    sostituto = p
                    break

            # 2. fallback qualsiasi ruolo
            if not sostituto:
                for p in panchina:
                    if p["voto"] > 0:
                        sostituto = p
                        break

        # 3. se trovato → sostituisce
        if sostituto:
            final.append(sostituto)
            panchina.remove(sostituto)

        # 4. se NON trovato → uomo in meno
        else:
            final.append({
                "nome": "NESSUNO",
                "ruolo": g["ruolo"],
                "voto": 0,
                "eventi": {}
            })

    return final


def punteggio_squadra(squadra):
    totale = 0

    for giocatore in squadra:
        totale += calcola_punteggio(
            giocatore["voto"],
            giocatore["eventi"]
        )

    return totale

def calcola_goal(punti):
    if punti < 66:
        return 0
    else:
        return int((punti - 66) // 4) + 1

squadra_A = [
    {"voto": 6, "eventi": {"gol segnato": 1}},
    {"voto": 6, "eventi": {"assist": 1}},
    {"voto": 6, "eventi": {}},
]

squadra_B = [
    {"voto": 6, "eventi": {"gol segnato": 1}},
    {"voto": 6, "eventi": {}},
    {"voto": 6, "eventi": {}},
]


posizioni_precedenti = {}

def aggiorna_posizioni():
    global posizioni_precedenti

    nuova = {}

    for i, (nome, s) in enumerate(classifica_ordinata()):
        nuova[nome] = i + 1

    posizioni_precedenti = nuova



def get_squadra(nome):
    if nome not in classifica:
        crea_squadra_classifica(nome)
    return classifica[nome]

def partita(nomeA, nomeB, squadraA, squadraB):
    global giornata_corrente

    print("PARTITA CHIAMATA:", nomeA, nomeB)

    if not valida_squadra(squadraA) or not valida_squadra(squadraB):
        print("Squadra non valida")
        return

    titolariA, panchinaA = prepara_formazione(squadraA)
    titolariB, panchinaB = prepara_formazione(squadraB)

    titolariA = sostituzioni(titolariA, panchinaA)
    titolariB = sostituzioni(titolariB, panchinaB)

    puntiA = punteggio_squadra(titolariA)
    puntiB = punteggio_squadra(titolariB)

    goalA = calcola_goal(puntiA)
    goalB = calcola_goal(puntiB)

    A = get_squadra(nomeA)
    B = get_squadra(nomeB)

    A["giocate"] += 1
    B["giocate"] += 1

    A["pf"] += puntiA
    B["pf"] += puntiB

    A["gf"] += goalA
    A["gs"] += goalB

    B["gf"] += goalB
    B["gs"] += goalA

    if goalA > goalB:
        A["v"] += 1
        A["pt"] += 3
        B["s"] += 1

    elif goalB > goalA:
        B["v"] += 1
        B["pt"] += 3
        A["s"] += 1

    else:
        A["p"] += 1
        B["p"] += 1
        A["pt"] += 1
        B["pt"] += 1

    conn = sqlite3.connect("fantalega.db")
    c = conn.cursor()

    c.execute("""
        INSERT INTO partite VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        giornata_corrente,
        nomeA,
        nomeB,
        goalA,
        goalB,
        puntiA,
        puntiB
    ))
        
    c.execute("""
        INSERT INTO punti_giornata VALUES (?, ?, ?)
    """, (giornata_corrente, nomeA, puntiA))

    c.execute("""
        INSERT INTO punti_giornata VALUES (?, ?, ?)
    """, (giornata_corrente, nomeB, puntiB))
    
    
    conn.commit()
    conn.close()
        
        
def carica_squadra(username,giornata):
    conn = sqlite3.connect("fantalega.db")
    c = conn.cursor()

    c.execute("SELECT nome, ruolo, tipo FROM formazioni WHERE username = ?", (username,))
    dati = c.fetchall()

    conn.close()

    squadra_nome = get_squadra_utente(username)

    squadre[squadra_nome]["titolari"] = []
    squadre[squadra_nome]["panchina"] = []

    for nome, ruolo, tipo in dati:
        voto, eventi = prendi_voto_eventi(nome, ruolo, giornata)

        giocatore = {
            "nome": nome,
            "ruolo": ruolo,
            "voto": voto,
            "eventi": eventi
        }

        if tipo == "titolare":
            squadre[squadra_nome]["titolari"].append(giocatore)
        else:
            squadre[squadra_nome]["panchina"].append(giocatore)


ADMIN_USER = "admin"

def is_admin():
    return session.get("user") == ADMIN_USER


import pandas as pd
import os


def importa_excel(giornata):
    file = "voti.xlsx"

    if not os.path.exists(file):
        return "File non trovato"

    df = pd.read_excel(file, skiprows=5)

    # PULIZIA NOMI COLONNE (IMPORTANTISSIMO)
    df.columns = df.columns.str.strip()

    # DEBUG (temporaneo)
    print(df.columns)
    
    df = df.rename(columns={
        "Ruolo": "Ruolo",
        "Nome": "Nome",
        "Voto": "Voto",
        "Gf": "Gf",
        "Gs": "Gs",
        "Rp": "Rp",
        "Rs": "Rs",
        "Rf": "Rf",
        "Au": "Au",
        "Amm": "Amm",
        "Esp": "Esp",
        "Ass": "Ass"
    })

    df = df[df["Ruolo"].astype(str).str.strip().isin(["P", "D", "C", "A"])]

    conn = sqlite3.connect("fantalega.db")
    c = conn.cursor()

    for _, row in df.iterrows():

        nome = row.get("Nome")
        ruolo = row.get("Ruolo")
        voto = pulisci_voto(row.get("Voto"))
        # conversione ruoli
        mappa_ruoli = {
            "P": "POR",
            "D": "DIF",
            "C": "CEN",
            "A": "ATT"
        }
        ruolo = mappa_ruoli.get(ruolo, ruolo)

    

        # bonus base Excel
        gol = int(row.get("Gf", 0) or 0)
        gs = int(row.get("Gs", 0) or 0)
        rig_par = int(row.get("Rp", 0) or 0)
        rig_sba = int(row.get("Rs", 0) or 0)
        rig_seg = int(row.get("Rf", 0) or 0)
        autogoal = int(row.get("Au", 0) or 0)
        amm = int(row.get("Amm", 0) or 0)
        esp = int(row.get("Esp", 0) or 0)
        assist = int(row.get("Ass", 0) or 0)

        potm = 0  # NON presente nel file

        # porta inviolata AUTOMATICA SOLO PORTIERE
        porta_inv = 1 if ruolo == "P" and gs == 0 and voto > 0 else 0

        c.execute("""
            INSERT OR REPLACE INTO voti_giornata
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            giornata,
            nome,
            voto,
            gol,
            assist,
            amm,
            esp,
            rig_par,
            rig_sba,
            rig_seg,
            autogoal,
            gs,
            porta_inv,
            potm
        ))

    conn.commit()
    conn.close()

    return "Import completato"

def aggiorna_stile_squadra(username, stemma=None, divisa=None):
    conn = sqlite3.connect("fantalega.db")
    c = conn.cursor()

    if stemma:
        c.execute("UPDATE utenti SET stemma = ? WHERE username = ?", (stemma, username))

    if divisa:
        c.execute("UPDATE utenti SET divisa = ? WHERE username = ?", (divisa, username))

    conn.commit()
    conn.close()

def pulisci_voto(v):
    if isinstance(v, str):
        v = v.replace("*", "")
        v = v.replace(",", ".")
    try:
        return float(v)
    except:
        return 0


def controlla_excel():
    file = "voti.xlsx"

    df = pd.read_excel(file, skiprows=5)

    return str(df.columns)

def get_squadra_utente(username):
    if username == "admin":
        return None

    conn = sqlite3.connect("fantalega.db")
    c = conn.cursor()

    c.execute("SELECT squadra FROM utenti WHERE username = ?", (username,))
    row = c.fetchone()

    if row and row[0]:
        squadra_nome = row[0]
    else:
        squadra_nome = f"Squadra {username}"
        c.execute("UPDATE utenti SET squadra = ? WHERE username = ?", (squadra_nome, username))
        conn.commit()

    conn.close()

    ensure_squadra(squadra_nome)
    crea_squadra_classifica(squadra_nome)

    return squadra_nome

def genera_partite():
    conn = sqlite3.connect("fantalega.db")
    c = conn.cursor()

    c.execute("SELECT squadra FROM utenti")
    nomi = [x[0] for x in c.fetchall()]

    conn.close()

    partite = []

    for i in range(len(nomi)):
        for j in range(i + 1, len(nomi)):
            partite.append((nomi[i], nomi[j]))

    return partite

# inizializza database
def init_db():
    conn = sqlite3.connect("fantalega.db")
    c = conn.cursor()

    # VOTI GIORNATA (UNICA TABELLA GIUSTA)
    c.execute("""
        CREATE TABLE IF NOT EXISTS utenti (
            username TEXT PRIMARY KEY,
            password TEXT,
            hint TEXT,
            squadra TEXT,
            stemma TEXT DEFAULT '',
            divisa TEXT DEFAULT '',
            role TEXT DEFAULT 'user'
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS voti_giornata (
            giornata INTEGER,
            nome TEXT,
            voto REAL,
            gol INTEGER,
            assist INTEGER,
            ammonizione INTEGER,
            espulsione INTEGER,
            rigore_parato INTEGER,
            rigore_sbagliato INTEGER,
            rigore_segnato INTEGER,
            autogoal INTEGER,
            goal_subito INTEGER,
            porta_inviolata INTEGER,
            player_of_the_match INTEGER,
            PRIMARY KEY (giornata, nome)
        )
    """)

    # FORMAZIONI
    c.execute("""
        CREATE TABLE IF NOT EXISTS formazioni (
            username TEXT,
            nome TEXT,
            ruolo TEXT,
            tipo TEXT
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS partite (
            giornata INTEGER,
            squadraA TEXT,
            squadraB TEXT,
            goalA INTEGER,
            goalB INTEGER,
            puntiA REAL,
            puntiB REAL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS punti_giornata (
            giornata INTEGER,
            squadra TEXT,
            punti REAL
        )
    """)

    conn.commit()
    conn.close()

def crea_admin():
    conn = sqlite3.connect("fantalega.db")
    c = conn.cursor()

    c.execute("SELECT * FROM utenti WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("""
            INSERT INTO utenti (username, password, hint, squadra, role)
            VALUES (?, ?, ?, NULL, ?)
        """, ("admin", "admin123", "admin account", "admin"))

    conn.commit()
    conn.close()

init_db()
crea_admin()
init_classifica_da_db()


# HOME
@app.route("/")
def home():
    user = session.get("user")
    role = session.get("role")

    if not user:
        return render_template("home.html", user=None)

    if role == "admin":
        return redirect("/admin")

    conn = sqlite3.connect("fantalega.db")
    c = conn.cursor()

    squadra = None
    c.execute("SELECT squadra FROM utenti WHERE username = ?", (user,))
    row = c.fetchone()
    if row:
        squadra = row[0]

    conn.close()

    return render_template("home.html", user=user, squadra=squadra)

# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        conn = sqlite3.connect("fantalega.db")
        c = conn.cursor()

        c.execute("SELECT password, role FROM utenti WHERE username = ?", (username,))
        result = c.fetchone()

        conn.close()

        if not result:
            return "❌ Utente non esiste"

        db_password, role = result

        if password != db_password:
            return "❌ Password errata"

        session.clear()  # 🔥 evita login "fantasma"
        session["user"] = username
        session["role"] = role

        return redirect("/")

    return render_template("login.html")
    
    
# DASHBOARD
@app.route("/dashboard")
def dashboard():
    username = session.get("user")
    role = session.get("role")

    if session.get("role") == "admin":
        return redirect("/admin")
    if "user" not in session:
        return redirect("/login")

    username = session["user"]

    conn = sqlite3.connect("fantalega.db")
    c = conn.cursor()

    c.execute("SELECT nome, ruolo, tipo FROM formazioni WHERE username = ?", (username,))
    dati = c.fetchall()

    c.execute("SELECT squadra, stemma, divisa FROM utenti WHERE username = ?", (username,))
    info = c.fetchone()

    conn.close()

    titolari = []
    panchina = []

    for nome, ruolo, tipo in dati:
        valore = f"{nome}|{ruolo}"

        if tipo == "titolare":
            titolari.append(valore)
        else:
            panchina.append(valore)

    return render_template(
        "dashboard.html",
        players=players,
        user=username,
        titolari=titolari,
        panchina=panchina,
        squadra_nome=info[0] if info else "",
        stemma=info[1] if info else "",
        divisa=info[2] if info else ""
    )


@app.route("/classifica")
def view_classifica():
    aggiorna_posizioni()

    return render_template(
        "classifica.html",
        classifica=classifica_ordinata(),
        pos_prec=posizioni_precedenti
    )

@app.route("/giornate")
def view_giornate():
    return render_template("giornate.html", giornate=giornate)




@app.route("/simula")
def simula():

    global giornata_corrente

    print("SQUADRE:", squadre)

    if len(squadre) < 2:
        print("Non ci sono abbastanza squadre")
        return redirect("/classifica")

    partite = genera_partite()

    print("PARTITE GENERATE:", partite)

    for A, B in partite:

        print("CHIAMO PARTITA:", A, B)

        if A not in squadre or B not in squadre:
            print("Squadra mancante:", A, B)
            continue

        if not valida_squadra(squadre[A]) or not valida_squadra(squadre[B]):
            print("Squadra non valida:", A, B)
            continue

        partita(A, B, squadre[A], squadre[B])

    giornata_corrente += 1

    return redirect("/classifica")

# SALVA FORMAZIONE
@app.route("/salva", methods=["POST"])
def salva():
    
    if session.get("role") == "admin":
        return "Admin non può creare formazione"
    username = session["user"]
    
    squadra_nome = get_squadra_utente(username)
    
    titolari_raw = request.form.getlist("titolari")
    panchina_raw = request.form.getlist("panchina")
    
    tutti = titolari_raw + panchina_raw

    # ❌ duplicati
    if len(tutti) != len(set(tutti)):
        return "Errore: hai selezionato giocatori duplicati"
    
    giocatori_validi = {f"{p['nome']}|{p['ruolo']}" for p in players}

    for g in tutti:
        if g not in giocatori_validi:
            return "Errore: giocatore non valido"

    if len(titolari_raw) + len(panchina_raw) == 0:
        return "Errore: formazione vuota"
    if len(titolari_raw) + len(panchina_raw) != 25:
        return "Errore: devi selezionare esattamente 25 giocatori"
    if len(titolari_raw) != 11:
        return "Errore: servono 11 titolari"
    
    porta = 0

    for x in titolari_raw:
        if "|POR" in x:
            porta += 1

    if porta != 1:
        return "Errore: devi avere esattamente 1 portiere titolare"
    
    squadra_nome = get_squadra_utente(username)
    
    
    rosa = []
    
    for x in (titolari_raw + panchina_raw):
        parts = x.split("|")
    
        if len(parts) != 2:
            continue

        rosa.append({
            "nome": parts[0],
            "ruolo": parts[1],
            "voto": 6,
            "eventi": {}
        })
    squadre[squadra_nome]["rosa"] = rosa
    
    squadre[squadra_nome]["titolari"] = [
        {"nome": x.split("|")[0], "ruolo": x.split("|")[1], "voto": 6, "eventi": {}}
        for x in titolari_raw
    ]

    squadre[squadra_nome]["panchina"] = [
        {
            "nome": x.split("|")[0],
            "ruolo": x.split("|")[1],
            "voto": 6,
            "eventi": {},
            "ordine": i + 1
            }
        for i, x in enumerate(panchina_raw)
    ]
    
    
    conn = sqlite3.connect("fantalega.db")
    c = conn.cursor()

    # cancella vecchia formazione
    c.execute("DELETE FROM formazioni WHERE username = ?", (username,))

    # salva titolari
    for x in titolari_raw:
        nome, ruolo = x.split("|")
        c.execute(
            "INSERT INTO formazioni VALUES (?, ?, ?, ?)",
            (username, nome, ruolo, "titolare")
        )

    # salva panchina
    for x in panchina_raw:
        nome, ruolo = x.split("|")
        c.execute(
            "INSERT INTO formazioni VALUES (?, ?, ?, ?)",
            (username, nome, ruolo, "panchina")
        )

    conn.commit()
    conn.close()
    
    return "Formazione salvata!"

@app.route("/debug_punti")
def debug_punti():
    conn = sqlite3.connect("fantalega.db")
    c = conn.cursor()

    c.execute("SELECT * FROM punti_giornata")
    dati = c.fetchall()

    conn.close()
    return str(dati)

@app.route("/debug_squadre")
def debug_squadre():
    return str(squadre)

@app.route("/debug_db")
def debug_db():
    conn = sqlite3.connect("fantalega.db")
    c = conn.cursor()

    c.execute("SELECT * FROM formazioni")
    dati = c.fetchall()

    conn.close()

    return str(dati)

@app.route("/admin_voti", methods=["GET", "POST"])
def admin_voti():
    if not is_admin():
        return "Accesso negato"

    if request.method == "POST":
        giornata = int(request.form["giornata"])

        conn = sqlite3.connect("fantalega.db")
        c = conn.cursor()

        for p in players:
            nome = p["nome"]

            voto = request.form.get(f"voto_{nome}")
            if voto is None or voto == "":
                continue

            gol = request.form.get(f"gol_{nome}", 0)
            assist = request.form.get(f"assist_{nome}", 0)
            ammonizione = request.form.get(f"amm_{nome}", 0)
            espulsione = request.form.get(f"esp_{nome}", 0)
            rig_par = request.form.get(f"rigpar_{nome}", 0)
            rig_sba = request.form.get(f"rigsba_{nome}", 0)
            rig_seg = request.form.get(f"rigseg_{nome}", 0)
            autogoal = request.form.get(f"auto_{nome}", 0)
            goal_subito = request.form.get(f"gs_{nome}", 0)
            porta_inv = request.form.get(f"pi_{nome}", 0)
            potm = request.form.get(f"potm_{nome}", 0)

            c.execute("""
                INSERT OR REPLACE INTO voti_giornata
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                giornata,
                nome,
                float(voto),
                int(gol or 0),
                int(assist or 0),
                int(ammonizione or 0),
                int(espulsione or 0),
                int(rig_par or 0),
                int(rig_sba or 0),
                int(rig_seg or 0),
                int(autogoal or 0),
                int(goal_subito or 0),
                int(porta_inv or 0),
                int(potm or 0)
            ))

        conn.commit()
        conn.close()

        return "Voti salvati!"

    return render_template("admin_voti.html", players=players)


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")

@app.route("/import_voti")
def import_voti():
    if not is_admin():
        return "Accesso negato"

    risultato = importa_excel(33)
    return risultato



@app.route("/test_excel")
def test_excel():
    return controlla_excel()


@app.route("/voti")
def voti():
    conn = sqlite3.connect("fantalega.db")
    c = conn.cursor()

    c.execute("SELECT * FROM voti_giornata")
    dati = c.fetchall()

    conn.close()

    return render_template("voti.html", dati=dati)


from flask import jsonify

@app.route("/api_andamento")
def api_andamento():

    conn = sqlite3.connect("fantalega.db")
    c = conn.cursor()

    # giornate ordinate
    c.execute("""
        SELECT DISTINCT giornata
        FROM punti_giornata
        ORDER BY giornata
    """)
    giornate = [g[0] for g in c.fetchall()]

    # squadre (evita nome variabile "squadre" che confonde col dict globale)
    c.execute("""
        SELECT DISTINCT squadra
        FROM punti_giornata
        WHERE squadra IS NOT NULL
    """)
    squadre_db = [s[0] for s in c.fetchall() if s[0] != "ADMIN_GLOBAL"]

    datasets = []

    for squadra in squadre_db:

        c.execute("""
            SELECT giornata, punti
            FROM punti_giornata
            WHERE squadra = ?
            ORDER BY giornata
        """, (squadra,))

        rows = c.fetchall()

        dati = {g: p for g, p in rows}

        datasets.append({
            "label": squadra,
            "data": [dati.get(g, 0) for g in giornate],
            "borderColor": "#38bdf8",
            "tension": 0.3,
            "fill": False
        })

    conn.close()

    # 🔥 fallback se DB vuoto
    if not datasets:
        return jsonify({
            "labels": [],
            "datasets": []
        })

    return jsonify({
        "labels": giornate,
        "datasets": datasets
    })


@app.route("/news")
def news():
    return render_template("news.html", giornate=giornate)


import json

@app.route("/grafico")
def grafico():
    return render_template("grafico.html")


@app.route("/debug_partite")
def debug_partite():
    conn = sqlite3.connect("fantalega.db")
    c = conn.cursor()

    c.execute("SELECT * FROM partite")
    dati = c.fetchall()

    conn.close()
    return str(dati)

@app.route("/settings", methods=["GET", "POST"])
def settings():
    if session.get("role") == "admin":
        return redirect("/admin")
    if "user" not in session:
        return redirect("/login")

    username = session["user"]

    conn = sqlite3.connect("fantalega.db")
    c = conn.cursor()

    if request.method == "POST":
        stemma = request.form.get("stemma", "")
        colore = request.form.get("colore", "#1f2937")
        pattern = request.form.get("pattern", "none")

        # salviamo divisa come JSON string
        colore2 = request.form.get("colore2", "#000000")

        divisa = f"{colore}|{colore2}|{pattern}"

        c.execute("""
            UPDATE utenti
            SET stemma = ?, divisa = ?
            WHERE username = ?
        """, (stemma, divisa, username))

        conn.commit()

    c.execute("SELECT squadra, stemma, divisa FROM utenti WHERE username = ?", (username,))
    data = c.fetchone()

    conn.close()

    return render_template("settings.html", data=data)

@app.route("/rosa")
def rosa():
    conn = sqlite3.connect("fantalega.db")
    c = conn.cursor()

    c.execute("SELECT squadra FROM utenti")
    squadre_lista = c.fetchall()

    dati = []

    for (squadra,) in squadre_lista:

        # 🚫 ESCLUDI ADMIN IN MODO DEFINITIVO
        if squadra is None or squadra == "ADMIN_GLOBAL" or squadra == "Squadra Admin":
            continue

        c.execute("""
            SELECT nome, ruolo
            FROM formazioni
            WHERE username = ?
        """, (squadra.replace("Squadra ", ""),))

        giocatori = c.fetchall()

        dati.append({
            "squadra": squadra,
            "giocatori": giocatori
        })

    conn.close()

    return render_template("rosa.html", dati=dati)

@app.route("/storico")
def storico():
    if session.get("role") == "admin":
        return redirect("/admin")
    conn = sqlite3.connect("fantalega.db")
    c = conn.cursor()

    c.execute("""
        SELECT giornata, squadraA, squadraB, goalA, goalB
        FROM partite
        ORDER BY giornata DESC
        LIMIT 10
    """)

    partite = c.fetchall()
    conn.close()

    return render_template("storico.html", partite=partite)

@app.route("/api_user")
def api_user():
    if "user" not in session:
        return {}

    username = session["user"]

    conn = sqlite3.connect("fantalega.db")
    c = conn.cursor()

    c.execute("SELECT squadra, stemma, divisa FROM utenti WHERE username = ?", (username,))
    data = c.fetchone()

    conn.close()

    if not data:
        return {}

    return {
        "squadra": data[0],
        "stemma": data[1],
        "divisa": data[2]
    }

@app.route("/calendario")
def calendario():
    conn = sqlite3.connect("fantalega.db")
    c = conn.cursor()

    c.execute("SELECT * FROM partite ORDER BY giornata DESC")
    partite = c.fetchall()

    conn.close()

    return render_template("calendario.html", partite=partite)

@app.route("/salva_formazione", methods=["POST"])
def salva_formazione():
    if "user" not in session:
        return "non loggato"

    username = session["user"]

    dati = request.json  # {tit, pan}

    conn = sqlite3.connect("fantalega.db")
    c = conn.cursor()

    c.execute("DELETE FROM formazioni WHERE username = ?", (username,))

    # TITOLARI
    for g in dati["titolari"]:
        nome, ruolo = g.split("|")
        c.execute(
            "INSERT INTO formazioni VALUES (?, ?, ?, ?)",
            (username, nome, ruolo, "titolare")
        )

    # PANCHINA
    for g in dati["panchina"]:
        nome, ruolo = g.split("|")
        c.execute(
            "INSERT INTO formazioni VALUES (?, ?, ?, ?)",
            (username, nome, ruolo, "panchina")
        )

    conn.commit()
    conn.close()

    return {"ok": True}


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"].strip()
        confirm = request.form["confirm"].strip()
        hint = request.form["hint"].strip()

        if password != confirm:
            return "❌ Password non coincidono"

        conn = sqlite3.connect("fantalega.db")
        c = conn.cursor()

        c.execute("SELECT username FROM utenti WHERE username = ?", (username,))
        if c.fetchone():
            conn.close()
            return "❌ Utente già esistente"
        if username == "admin":
            return "Username non valido"
        squadra_nome = f"Squadra {username}"

        c.execute("""
            INSERT INTO utenti (username, password, hint, squadra, role)
            VALUES (?, ?, ?, ?, 'user')
        """, (username, password, hint, squadra_nome))

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")


@app.route("/recover", methods=["GET", "POST"])
def recover():
    data = None

    if request.method == "POST":
        username = request.form["username"]

        conn = sqlite3.connect("fantalega.db")
        c = conn.cursor()

        c.execute("SELECT password, hint FROM utenti WHERE username = ?", (username,))
        data = c.fetchone()

        conn.close()

        if not data:
            return "❌ Utente non trovato"

    return render_template("recover.html", data=data)

@app.route("/debug_role")
def debug_role():
    return str(session.get("role"))

@app.before_request
def blocca_accesso_admin_in_register():
    if request.endpoint == "register" and session.get("user") == "admin":
        return redirect("/")

@app.route("/admin")
def admin_home():
    if session.get("role") != "admin":
        return redirect("/")

    return render_template("admin_home.html")

from flask import render_template


if __name__ == "__main__":
    app.run(debug=True)
