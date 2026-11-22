"""
Generate Brett Stehouwer's FE Express Job Application PDF
Compiles a publication-grade, print-ready 8.5x11 PDF using Typst.
Outputs to:
- C:\\AI-BS\\saved_data\\publications\\Brett_Stehouwer_FE_Express_Job_Application.pdf
- C:\\AI-BS\\Brett_Stehouwer_FE_Express_Job_Application.pdf
- C:\\AI-BS\\docs\\Brett_Stehouwer_FE_Express_Job_Application.pdf
"""

import os
import sys
import tempfile
import typst
import pypdf

TYPST_CONTENT = """
#set page(
  paper: "us-letter",
  margin: (x: 0.45in, top: 0.38in, bottom: 0.38in),
  header: [
    #grid(
      columns: (1fr, 1fr),
      align(left)[
        #text(size: 7pt, fill: rgb("64748b"), weight: "bold")[
          FE EXPRESS — FORMAL EMPLOYMENT APPLICATION
        ]
      ],
      align(right)[
        #text(size: 7pt, fill: rgb("64748b"))[
          Applicant: Brett Adam Stehouwer • (616) 600-3837
        ]
      ]
    )
    #v(-2pt)
    #line(length: 100%, stroke: 0.5pt + rgb("cbd5e1"))
  ],
  footer: [
    #line(length: 100%, stroke: 0.5pt + rgb("cbd5e1"))
    #v(1pt)
    #grid(
      columns: (1fr, 1fr),
      align(left)[
        #text(size: 7pt, fill: rgb("94a3b8"))[
          FE Express Operations & Logistics Division • Confidential Candidate Portfolio
        ]
      ],
      align(right)[
        #text(size: 7pt, fill: rgb("94a3b8"))[
          Page 1 of 1 • Standard Letter (8.5x11)
        ]
      ]
    )
  ]
)

#set text(
  font: ("Segoe UI", "Arial", "Helvetica", "DejaVu Sans"),
  size: 8.2pt,
  fill: rgb("1e293b"),
  lang: "en"
)

#set par(
  leading: 0.45em,
  justify: false
)

// Header Banner
#block(
  fill: rgb("0f172a"),
  inset: (x: 14pt, y: 10pt),
  radius: 4pt,
  width: 100%,
  stroke: 1pt + rgb("1e293b")
)[
  #grid(
    columns: (1fr, auto),
    gutter: 8pt,
    [
      #text(size: 15pt, weight: "bold", fill: rgb("f8fafc"))[APPLICATION FOR EMPLOYMENT] \\
      #v(2pt)
      #text(size: 10pt, weight: "bold", fill: rgb("38bdf8"))[FE EXPRESS]
      #text(size: 9pt, fill: rgb("cbd5e1"))[ — Logistics / Route Driver / Operations Specialist]
    ],
    align(right + horizon)[
      #block(
        fill: rgb("1e293b"),
        inset: (x: 8pt, y: 5pt),
        radius: 3pt,
        stroke: 0.5pt + rgb("334155")
      )[
        #text(size: 7.5pt, weight: "bold", fill: rgb("10b981"))[STATUS: READY FOR REVIEW] \\
        #text(size: 7pt, fill: rgb("cbd5e1"))[Availability: Immediate / Full-Time]
      ]
    ]
  )
]

#v(4pt)

// Section 1: Applicant Identification & Contact Details
#block(
  fill: rgb("f8fafc"),
  inset: (x: 10pt, y: 7pt),
  radius: 4pt,
  stroke: 0.6pt + rgb("e2e8f0"),
  width: 100%
)[
  #text(size: 9pt, weight: "bold", fill: rgb("0f172a"))[1. Applicant Identification & Contact Details]
  #v(2pt)
  #line(length: 100%, stroke: 0.4pt + rgb("cbd5e1"))
  #v(4pt)
  #grid(
    columns: (1.2fr, 1.1fr, 1.4fr),
    row-gutter: 5pt,
    column-gutter: 10pt,
    [
      #text(weight: "bold", size: 7.2pt, fill: rgb("64748b"))[FULL NAME] \\
      #text(weight: "bold", size: 8.5pt, fill: rgb("0f172a"))[Brett Adam Stehouwer]
    ],
    [
      #text(weight: "bold", size: 7.2pt, fill: rgb("64748b"))[PHONE NUMBER] \\
      #text(weight: "medium", size: 8.5pt, fill: rgb("0f172a"))[(616) 600-3837]
    ],
    [
      #text(weight: "bold", size: 7.2pt, fill: rgb("64748b"))[EMAIL ADDRESS] \\
      #text(weight: "medium", size: 8.5pt, fill: rgb("0284c7"))[#link("mailto:BrettStehouwer@gmail.com")[BrettStehouwer\\@gmail.com]]
    ],
    [
      #text(weight: "bold", size: 7.2pt, fill: rgb("64748b"))[LOCATION BASE] \\
      #text(weight: "medium", size: 8.5pt, fill: rgb("0f172a"))[Jenison, Michigan]
    ],
    [
      #text(weight: "bold", size: 7.2pt, fill: rgb("64748b"))[TARGET COMPANY] \\
      #text(weight: "bold", size: 8.5pt, fill: rgb("0f172a"))[FE Express]
    ],
    [
      #text(weight: "bold", size: 7.2pt, fill: rgb("64748b"))[WORK AUTHORIZATION] \\
      #text(weight: "medium", size: 8.5pt, fill: rgb("10b981"))[Authorized in the United States]
    ],
    [
      #text(weight: "bold", size: 7.2pt, fill: rgb("64748b"))[POSITION DESIRED] \\
      #text(weight: "bold", size: 8.2pt, fill: rgb("0f172a"))[Logistics / Route Driver / Operations Specialist]
    ],
    [
      #text(weight: "bold", size: 7.2pt, fill: rgb("64748b"))[AVAILABILITY] \\
      #text(weight: "medium", size: 8.5pt, fill: rgb("0f172a"))[Immediate / Full-Time]
    ],
    [
      #text(weight: "bold", size: 7.2pt, fill: rgb("64748b"))[RESIDENCY REGION] \\
      #text(weight: "medium", size: 8.5pt, fill: rgb("0f172a"))[West Michigan Regional Corridors]
    ]
  )
]

#v(4pt)

// Section 2: Operational & Professional Work History
#block(
  fill: rgb("ffffff"),
  inset: (x: 10pt, y: 7pt),
  radius: 4pt,
  stroke: 0.6pt + rgb("e2e8f0"),
  width: 100%
)[
  #text(size: 9pt, weight: "bold", fill: rgb("0f172a"))[2. Operational & Professional Work History]
  #v(2pt)
  #line(length: 100%, stroke: 0.4pt + rgb("cbd5e1"))
  #v(4pt)

  // Position 1
  #grid(
    columns: (1fr, auto),
    [
      #text(weight: "bold", size: 8.5pt, fill: rgb("0f172a"))[Logistics & Route Delivery Specialist]
      #text(size: 8pt, fill: rgb("475569"))[ | Freight Logistics / Independent Delivery]
    ],
    [
      #text(weight: "bold", size: 7.5pt, fill: rgb("0284c7"))[West Michigan Regional Corridors]
    ]
  )
  #v(1pt)
  #list(
    marker: [•],
    body-indent: 5pt,
    tight: true,
    [Executed high-volume time-sensitive multi-stop delivery routes across freight logistics, Amazon, and DoorDash platforms.],
    [Maintained preventative vehicle inspections, load tie-down security, cargo integrity, and GPS route optimization.],
    [Achieved zero-loss fulfillment with 100% on-time completion under variable weather and traffic conditions.]
  )

  #v(3pt)

  // Position 2
  #grid(
    columns: (1fr, auto),
    [
      #text(weight: "bold", size: 8.5pt, fill: rgb("0f172a"))[Store Lead & Hardware Repair Specialist]
      #text(size: 8pt, fill: rgb("475569"))[ | uBreakiFix]
    ],
    [
      #text(weight: "bold", size: 7.5pt, fill: rgb("0284c7"))[Store Management & Technical Service]
    ]
  )
  #v(1pt)
  #list(
    marker: [•],
    body-indent: 5pt,
    tight: true,
    [Led daily store operations, employee scheduling, customer intake, and point-of-sale inventory audits.],
    [Diagnosed and repaired complex board-level electronics, handled component-level triage, micro-soldering, and device testing.],
    [Maintained rapid turnaround windows and strict diagnostic quality assurance standards.]
  )

  #v(3pt)

  // Position 3
  #grid(
    columns: (1fr, auto),
    [
      #text(weight: "bold", size: 8.5pt, fill: rgb("0f172a"))[Direct Residential Care Specialist]
      #text(size: 8pt, fill: rgb("475569"))[ | Hope Network]
    ],
    [
      #text(weight: "bold", size: 7.5pt, fill: rgb("0284c7"))[Compliance & Direct Care Operations]
    ]
  )
  #v(1pt)
  #list(
    marker: [•],
    body-indent: 5pt,
    tight: true,
    [Provided daily living assistance, medical adherence monitoring, and direct care for residents requiring behavioral and neurological support.],
    [Enforced state healthcare regulatory protocols, detailed daily shift logs, and strict chain-of-custody documentation.]
  )

  #v(3pt)

  // Position 4
  #grid(
    columns: (1fr, auto),
    [
      #text(weight: "bold", size: 8.5pt, fill: rgb("0f172a"))[Founder & Systems Architect]
      #text(size: 8pt, fill: rgb("475569"))[ | AI-BS Framework / Stehouwer Publishing LLC]
    ],
    [
      #text(weight: "bold", size: 7.5pt, fill: rgb("0284c7"))[Operational Oversight & Autonomous Systems]
    ]
  )
  #v(1pt)
  #list(
    marker: [•],
    body-indent: 5pt,
    tight: true,
    [Directed sovereign infrastructure, data orchestration workflows, and local network operations.],
    [Managed procurement, client communications, production deadlines, and digital document compilation.]
  )
]

#v(4pt)

// Section 3: Core Competencies & Skills Matrix
#block(
  fill: rgb("ffffff"),
  inset: (x: 10pt, y: 6pt),
  radius: 4pt,
  stroke: 0.6pt + rgb("e2e8f0"),
  width: 100%
)[
  #text(size: 9pt, weight: "bold", fill: rgb("0f172a"))[3. Core Competencies & Skills Matrix]
  #v(2pt)
  #line(length: 100%, stroke: 0.4pt + rgb("cbd5e1"))
  #v(3pt)

  #table(
    columns: (1.3fr, 3.7fr),
    stroke: (x, y) => if y == 0 { (bottom: 1pt + rgb("0f172a")) } else { (bottom: 0.4pt + rgb("e2e8f0")) },
    fill: (x, y) => if y == 0 { rgb("f1f5f9") } else if calc.even(y) { rgb("f8fafc") } else { rgb("ffffff") },
    inset: (x: 7pt, y: 4pt),
    align: (col, row) => if row == 0 { (left + horizon) } else { (left + horizon) },
    table.header(
      [*Operational Area*],
      [*Qualifications & Capabilities*]
    ),
    [#text(weight: "bold", fill: rgb("0f172a"))[Logistics & Delivery]],
    [Route planning, multi-drop dispatch, cargo stabilization, fuel efficiency, time management],

    [#text(weight: "bold", fill: rgb("0f172a"))[Mechanical & Technical]],
    [Preventative vehicle maintenance, electrical/hardware diagnostics, tool bench operations],

    [#text(weight: "bold", fill: rgb("0f172a"))[Compliance & Safety]],
    [Chain of custody logging, regulatory adherence, incident reporting, accountability],

    [#text(weight: "bold", fill: rgb("0f172a"))[Communication & Systems]],
    [Mobile dispatch apps, inventory management systems, client service intake]
  )
]

#v(4pt)

// Section 4: Applicant Attestation & Authorization
#block(
  fill: rgb("f8fafc"),
  inset: (x: 10pt, y: 6pt),
  radius: 4pt,
  stroke: 0.6pt + rgb("cbd5e1"),
  width: 100%
)[
  #text(size: 8pt, weight: "bold", fill: rgb("0f172a"))[4. Applicant Attestation & Authorization]
  #v(2pt)
  #text(size: 7.2pt, fill: rgb("475569"))[
    I certify that all statements and information provided in this employment application are true, correct, and complete to the best of my knowledge. I understand that any false statements or omissions may disqualify me from employment consideration or result in immediate termination if employed. I authorize FE Express to verify my employment history, qualifications, and operational driving records.
  ]
  #v(6pt)
  #grid(
    columns: (1.8fr, 1.1fr, 1.1fr),
    gutter: 12pt,
    [
      #line(length: 100%, stroke: 0.6pt + rgb("94a3b8"))
      #v(1pt)
      #text(size: 7.5pt, weight: "bold", fill: rgb("0f172a"))[Applicant Signature: ]
      #text(size: 8pt, style: "italic", fill: rgb("1e40af"))[/s/ Brett Adam Stehouwer]
    ],
    [
      #line(length: 100%, stroke: 0.6pt + rgb("94a3b8"))
      #v(1pt)
      #text(size: 7.5pt, weight: "bold", fill: rgb("0f172a"))[Date: ]
      #text(size: 7.5pt, fill: rgb("334155"))[October 7, 2026]
    ],
    [
      #line(length: 100%, stroke: 0.6pt + rgb("94a3b8"))
      #v(1pt)
      #text(size: 7.5pt, weight: "bold", fill: rgb("0f172a"))[Location: ]
      #text(size: 7.5pt, fill: rgb("334155"))[Jenison, MI]
    ]
  )
]
"""

def generate_pdf():
    print("Compiling Brett Stehouwer's FE Express Job Application PDF...")
    
    with tempfile.NamedTemporaryFile(suffix=".typ", mode="w", encoding="utf-8", delete=False) as tf:
        tf.write(TYPST_CONTENT)
        temp_typ = tf.name

    try:
        pdf_bytes = typst.compile(temp_typ)
        print(f"Compilation successful: {len(pdf_bytes)} bytes.")
    finally:
        if os.path.exists(temp_typ):
            os.remove(temp_typ)

    # Destination paths
    destinations = [
        r"C:\AI-BS\saved_data\publications\Brett_Stehouwer_FE_Express_Job_Application.pdf",
        r"C:\AI-BS\Brett_Stehouwer_FE_Express_Job_Application.pdf",
        r"C:\AI-BS\docs\Brett_Stehouwer_FE_Express_Job_Application.pdf"
    ]

    for dest in destinations:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(pdf_bytes)
        size_kb = round(os.path.getsize(dest) / 1024, 2)
        print(f"  [SAVED] {dest} ({size_kb} KB)")

    reader = pypdf.PdfReader(destinations[0])
    page_count = len(reader.pages)
    print(f"[VERIFICATION] Document Page Count: {page_count} (Standard Letter 8.5x11)")
    return page_count == 1

if __name__ == "__main__":
    success = generate_pdf()
    sys.exit(0 if success else 1)
