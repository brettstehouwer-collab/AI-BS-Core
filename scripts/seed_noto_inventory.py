import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "aibs_master.db")

def init_noto_tables():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS noto_inventory_items (
        id TEXT PRIMARY KEY,
        location TEXT NOT NULL,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        par_level INTEGER NOT NULL,
        upstairs TEXT DEFAULT '0',
        downstairs TEXT DEFAULT '0',
        banquet_a TEXT DEFAULT '0',
        banquet_b TEXT DEFAULT '0',
        patio TEXT DEFAULT '0',
        cellar_bin TEXT DEFAULT 'N/A',
        storeroom TEXT DEFAULT '0',
        distributor TEXT DEFAULT '',
        status TEXT DEFAULT 'FULL',
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS noto_dispatch_queue (
        id TEXT PRIMARY KEY,
        location TEXT DEFAULT 'GR',
        target_bar TEXT NOT NULL,
        item TEXT NOT NULL,
        source_loc TEXT NOT NULL,
        time TEXT NOT NULL,
        requested_by TEXT NOT NULL,
        status TEXT DEFAULT 'PENDING'
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS noto_sos_calls (
        id TEXT PRIMARY KEY,
        location TEXT DEFAULT 'GR',
        bar TEXT NOT NULL,
        type TEXT NOT NULL,
        urgency TEXT DEFAULT 'NORMAL',
        time TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS noto_86_board (
        id TEXT PRIMARY KEY,
        location TEXT DEFAULT 'GR',
        item TEXT NOT NULL,
        station TEXT NOT NULL,
        reason TEXT NOT NULL,
        alt_suggestion TEXT,
        time TEXT NOT NULL
    );
    """)

    # Check item count
    cur.execute("SELECT COUNT(*) FROM noto_inventory_items")
    count = cur.fetchone()[0]

    if count == 0:
        items = [
            # Grand Rapids (GR)
            ('INV-GR-101', 'GR', "Tito's Handmade Vodka (750ml)", 'Spirits (Vodka)', 12, '0', '1', '3', '2', '0', 'Vault N/A', '8 (Rack 2, Shelf B)', "Southern Glazer's", 'LOW'),
            ('INV-GR-102', 'GR', 'Grey Goose Vodka (1L)', 'Spirits (Vodka)', 8, '2', '2', '1', '1', '1', 'Vault N/A', '5 (Rack 2, Shelf A)', "Southern Glazer's", 'FULL'),
            ('INV-GR-103', 'GR', 'Ketel One Botanical Peach & Orange (750ml)', 'Spirits (Vodka)', 6, '1', '1', '0', '0', '1', 'Vault N/A', '3 (Rack 2, Shelf C)', "Southern Glazer's", 'FULL'),
            ('INV-GR-104', 'GR', 'Casamigos Blanco Tequila (750ml)', 'Spirits (Tequila)', 10, '1', '2', '2', '1', '1', 'Vault N/A', '6 (Rack 1, Shelf A)', 'RNDC', 'LOW'),
            ('INV-GR-105', 'GR', 'Casamigos Reposado Tequila (750ml)', 'Spirits (Tequila)', 8, '2', '1', '1', '1', '0', 'Vault N/A', '4 (Rack 1, Shelf B)', 'RNDC', 'FULL'),
            ('INV-GR-106', 'GR', 'Don Julio 1942 Añejo Tequila', 'Spirits (Tequila)', 4, '1', '1', '0', '0', '0', 'Vault Reserve', '3 (Rack 1, Shelf C)', 'RNDC', 'FULL'),
            ('INV-GR-107', 'GR', 'Clase Azul Reposado Tequila (750ml)', 'Spirits (Tequila)', 3, '1', '0', '0', '0', '0', 'Vault Reserve', '2 (Locked Cage)', 'RNDC', 'FULL'),
            ('INV-GR-108', 'GR', 'Woodford Reserve Bourbon (750ml)', 'Spirits (Whiskey)', 8, '2', '2', '1', '1', '1', 'N/A', '5 (Rack 3, Shelf A)', "Southern Glazer's", 'FULL'),
            ('INV-GR-109', 'GR', 'Buffalo Trace Kentucky Bourbon (750ml)', 'Spirits (Whiskey)', 6, '1', '0', '1', '0', '0', 'N/A', '2 (Rack 3, Shelf B)', 'Great Lakes Wine & Spirits', 'CRITICAL'),
            ('INV-GR-110', 'GR', "Maker's Mark 46 Bourbon (750ml)", 'Spirits (Whiskey)', 6, '2', '1', '1', '0', '1', 'N/A', '4 (Rack 3, Shelf C)', "Southern Glazer's", 'FULL'),
            ('INV-GR-111', 'GR', 'The Macallan 12yr Double Cask (750ml)', 'Scotch Single Malt', 5, '1', '1', '0', '0', '0', 'Vault Reserve', '3 (Rack 4, Shelf A)', 'RNDC', 'FULL'),
            ('INV-GR-112', 'GR', 'Johnnie Walker Blue Label (750ml)', 'Scotch Blended', 3, '1', '0', '0', '0', '0', 'Vault Reserve', '2 (Locked Cage)', 'RNDC', 'FULL'),
            ('INV-GR-113', 'GR', "Hendrick's Scottish Gin (750ml)", 'Spirits (Gin)', 8, '2', '2', '1', '1', '1', 'N/A', '6 (Rack 2, Shelf D)', 'RNDC', 'FULL'),
            ('INV-GR-114', 'GR', 'Tanqueray No. Ten Gin (750ml)', 'Spirits (Gin)', 6, '1', '1', '0', '0', '0', 'N/A', '4 (Rack 2, Shelf D)', "Southern Glazer's", 'FULL'),
            ('INV-GR-115', 'GR', '2016 Tenuta San Guido Sassicaia', 'Fine Wine (Tuscany)', 6, '0', '0', '0', '0', '0', 'Aisle 3 • Rack D • Bin 14', '18 (Cellar Vault)', 'Great Lakes Wine & Spirits', 'FULL'),
            ('INV-GR-116', 'GR', '2015 Biondi-Santi Brunello di Montalcino', 'Fine Wine (Tuscany)', 4, '0', '0', '0', '0', '0', 'Aisle 1 • Rack B • Bin 08', '12 (Cellar Vault)', 'Great Lakes Wine & Spirits', 'FULL'),
            ('INV-GR-117', 'GR', '2018 Tignanello Antinori (750ml)', 'Fine Wine (Tuscany)', 8, '0', '0', '0', '0', '0', 'Aisle 2 • Rack C • Bin 04', '14 (Cellar Vault)', 'Great Lakes Wine & Spirits', 'FULL'),
            ('INV-GR-118', 'GR', '2019 Ornellaia Bolgheri Superiore', 'Fine Wine (Tuscany)', 6, '0', '0', '0', '0', '0', 'Aisle 3 • Rack A • Bin 11', '8 (Cellar Vault)', 'Great Lakes Wine & Spirits', 'FULL'),
            ('INV-GR-119', 'GR', '2017 Barolo Bartolo Mascarello', 'Fine Wine (Piedmont)', 4, '0', '0', '0', '0', '0', 'Aisle 4 • Rack B • Bin 02', '6 (Cellar Vault)', 'Great Lakes Wine & Spirits', 'FULL'),
            ('INV-GR-120', 'GR', 'Veuve Clicquot Yellow Label Brut', 'Champagne', 12, '1', '2', '4', '2', '0', 'Wine Cooler 2', '16 (Cellar Vault)', "Southern Glazer's", 'FULL'),
            ('INV-GR-121', 'GR', 'Dom Pérignon Vintage 2013 (750ml)', 'Champagne', 6, '0', '0', '1', '0', '0', 'Vault Reserve Bin 01', '5 (Cellar Vault)', "Southern Glazer's", 'FULL'),
            ('INV-GR-122', 'GR', 'Peroni Nastro Azzurro Draft Keg (1/2 Bbl)', 'Draft Beer', 4, '85% (Tap 1)', '90% (Tap 2)', '0% (OUT)', '50% (Tap 1)', '70% (Tap 1)', 'N/A', '2 Backup Kegs', 'Imperial Beverage', 'LOW'),
            ('INV-GR-123', 'GR', "Bell's Two Hearted Ale (1/2 Bbl Keg)", 'Draft Beer', 4, '60% (Tap 2)', '75% (Tap 1)', '40% (Tap 2)', '0% (OUT)', '80% (Tap 2)', 'N/A', '3 Backup Kegs', 'Alliance Beverage', 'FULL'),
            ('INV-GR-124', 'GR', 'Founders All Day IPA (1/2 Bbl Keg)', 'Draft Beer', 3, '50% (Tap 3)', '40% (Tap 3)', '20% (Tap 3)', '60% (Tap 2)', '30% (Tap 3)', 'N/A', '2 Backup Kegs', 'Alliance Beverage', 'FULL'),
            ('INV-GR-125', 'GR', 'Stella Artois European Lager (50L)', 'Draft Beer', 3, '70% (Tap 4)', '60% (Tap 4)', '0% (Tap 4)', '0% (Tap 3)', '50% (Tap 4)', 'N/A', '1 Backup Keg', 'Imperial Beverage', 'LOW'),
            ('INV-GR-126', 'GR', 'Campari Bitter Aperitivo (1L)', 'Liqueurs & Cordials', 6, '1', '1', '0', '0', '1', 'N/A', '4 (Rack 5, Shelf A)', 'RNDC', 'FULL'),
            ('INV-GR-127', 'GR', 'Aperol Aperitivo (1L)', 'Liqueurs & Cordials', 8, '2', '2', '1', '1', '2', 'N/A', '6 (Rack 5, Shelf B)', 'RNDC', 'FULL'),
            ('INV-GR-128', 'GR', 'Disaronno Originale Amaretto (750ml)', 'Liqueurs & Cordials', 6, '1', '1', '1', '1', '0', 'N/A', '4 (Rack 5, Shelf C)', "Southern Glazer's", 'FULL'),
            ('INV-GR-129', 'GR', 'Fever-Tree Indian Tonic (24ct Case)', 'Mixers & Provisions', 10, '2 cs', '1 cs', '2 cs', '1 cs', '1 cs', 'Dry Storage', '8 cs (Bay 4)', 'Imperial Beverage', 'FULL'),
            ('INV-GR-130', 'GR', 'Luxardo Gourmet Maraschino Cherries (3kg)', 'Garnishes', 4, '1 tub', '1 tub', '0', '0', '1 tub', 'Dry Storage', '3 tubs (Shelf G)', 'Sysco Specialty', 'FULL'),

            # Grand Haven (GH)
            ('INV-GH-201', 'GH', "Tito's Handmade Vodka (750ml)", 'Spirits (Vodka)', 8, '1', '2', '0', '0', '2', 'N/A', '6 (Storeroom Main)', "Southern Glazer's", 'FULL'),
            ('INV-GH-202', 'GH', 'Casamigos Blanco Tequila (750ml)', 'Spirits (Tequila)', 6, '1', '1', '0', '0', '1', 'N/A', '4 (Storeroom Main)', 'RNDC', 'FULL'),
            ('INV-GH-203', 'GH', '2017 Tenuta San Guido Sassicaia', 'Fine Wine (Tuscany)', 4, '0', '0', '0', '0', '0', 'Wine Locker GH-1', '6 (Cellar Storage)', 'Great Lakes Wine & Spirits', 'FULL'),
            ('INV-GH-204', 'GH', 'Santa Margherita Pinot Grigio (750ml)', 'Fine Wine (Veneto)', 12, '3', '2', '0', '0', '4', 'Wine Cooler 1', '14 (Cellar Storage)', 'Great Lakes Wine & Spirits', 'FULL'),
            ('INV-GH-205', 'GH', 'Peroni Nastro Azzurro Draft Keg (1/2 Bbl)', 'Draft Beer', 3, '90% (Tap 1)', '70% (Tap 1)', '0', '0', '85% (Patio Tap)', 'N/A', '2 Backup Kegs', 'Imperial Beverage', 'FULL'),
            ('INV-GH-206', 'GH', 'New Holland Tangerine Space Machine Keg', 'Draft Beer', 3, '50% (Tap 2)', '60% (Tap 2)', '0', '0', '40% (Patio Tap)', 'N/A', '2 Backup Kegs', 'Alliance Beverage', 'FULL'),
            ('INV-GH-207', 'GH', 'Aperol Aperitivo (1L)', 'Liqueurs & Cordials', 6, '2', '1', '0', '0', '2', 'N/A', '5 (Storeroom Main)', 'RNDC', 'FULL'),
            ('INV-GH-208', 'GH', 'High Noon Sun Sips Variety Pack (24ct)', 'RTD Seltzers', 8, '1 cs', '1 cs', '0', '0', '2 cs', 'Cooler 2', '6 cs (Bay 2)', 'Alliance Beverage', 'FULL')
        ]

        cur.executemany("""
        INSERT INTO noto_inventory_items 
        (id, location, name, category, par_level, upstairs, downstairs, banquet_a, banquet_b, patio, cellar_bin, storeroom, distributor, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, items)

        # Seed initial dispatch
        dispatches = [
            ('DISP-801', 'GR', 'Upstairs Main Bar (Well 1)', "2x Tito's Handmade Vodka", 'Central Storeroom — Rack 2, Shelf B', '6:42 PM', 'Bartender Alex', 'PENDING'),
            ('DISP-802', 'GR', 'Banquet Bar A (Grand Ballroom)', '1x Backup Peroni Draft Keg', 'Basement Beer Cooler — Station 4', '6:38 PM', 'Banquet Lead Sam', 'EN_ROUTE'),
            ('DISP-803', 'GH', 'Patio Deck Bar', '1x Case High Noon Variety', 'GH Cold Box — Bay 2', '6:50 PM', 'Lead Server Marcus', 'PENDING')
        ]
        cur.executemany("INSERT INTO noto_dispatch_queue VALUES (?, ?, ?, ?, ?, ?, ?, ?)", dispatches)

        # Seed SOS calls
        sos = [
            ('SOS-01', 'GR', 'Upstairs Main Bar', '🧊 Need Ice Bin Refill', 'HIGH', '6:45 PM'),
            ('SOS-02', 'GR', 'Downstairs Lounge', '🍸 Need Clean Rocks / Coupe Glasses', 'NORMAL', '6:41 PM'),
            ('SOS-03', 'GH', 'Patio Deck Bar', '🍋 Need Cut Lemons & Limes (Bar Prep)', 'NORMAL', '6:48 PM')
        ]
        cur.executemany("INSERT INTO noto_sos_calls VALUES (?, ?, ?, ?, ?, ?)", sos)

        # Seed 86 board
        eightysix = [
            ('86-901', 'GR', 'Chilean Sea Bass (Fresh Catch)', 'Kitchen Expo Line', '38 portions sold out; delivery 8 AM tomorrow', 'Grilled Mediterranean Halibut', '6:14 PM'),
            ('86-902', 'GR', 'Casamigos Añejo Tequila', 'Upstairs & Downstairs Bars', 'Depleted during high-volume rush', 'Don Julio 1942 or Patron Reposado', '6:30 PM'),
            ('86-903', 'GH', 'Fresh Watercress Salad', 'GH Kitchen Expo', 'Local supplier shipment delayed', 'Baby Arugula Salad with Shaved Fennel', '5:50 PM')
        ]
        cur.executemany("INSERT INTO noto_86_board VALUES (?, ?, ?, ?, ?, ?, ?)", eightysix)

        conn.commit()
        print(f"[Seed] Successfully populated {len(items)} Noto inventory items, {len(dispatches)} dispatch items, {len(sos)} SOS calls, and {len(eightysix)} 86 board records into {DB_PATH}")
    else:
        print(f"[Seed] noto_inventory_items table already contains {count} records. No seed required.")

    conn.close()

if __name__ == "__main__":
    init_noto_tables()
