from flask import Flask, request, jsonify

app = Flask(__name__)

SANCTIONS_DB = {
    "Juan Pérez": {
        "lists": ["OFAC SDN", "EU Consolidated"],
        "reason": "Vinculación con lavado de activos",
        "date_added": "2023-03-15"
    },
    "María García": {
        "lists": ["UN Security Council"],
        "reason": "Financiamiento de terrorismo",
        "date_added": "2022-11-20"
    }
}

OWNERSHIP_DATA = {
    "Empresa XYZ S.A.S.": {
        "owners": [
            {"name": "Carlos Rodríguez", "percentage": 45},
            {"name": "Empresa ABC Ltda.", "percentage": 55}
        ],
        "jurisdiction": "Colombia",
        "incorporation_date": "2018-05-12"
    },
    "Empresa ABC Ltda.": {
        "owners": [
            {"name": "Juan Pérez", "percentage": 60},
            {"name": "Inversiones XYZ S.A.", "percentage": 40}
        ],
        "jurisdiction": "Panamá",
        "incorporation_date": "2015-08-22"
    }
}

@app.route('/')
def index():
    return '''
    <html>
    <head>
        <title>ComplianceAI - Demo</title>
        <style>
            body { font-family: Arial; max-width: 800px; margin: 0 auto; padding: 20px; }
            .result { background: #f5f5f5; padding: 20px; border-radius: 8px; margin-top: 20px; }
            .critical { color: #dc3545; font-weight: bold; }
            .high { color: #fd7e14; font-weight: bold; }
            .medium { color: #ffc107; font-weight: bold; }
            .low { color: #28a745; font-weight: bold; }
            .alert { background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 10px 0; }
            .critical-alert { background: #f8d7da; border-left: 4px solid #dc3545; padding: 10px; margin: 10px 0; }
        </style>
    </head>
    <body>
        <h1>ComplianceAI - Sanctions Screening Demo</h1>
        <p>Enter an entity name to screen against sanctions lists and analyze ownership structure.</p>
        
        <input type="text" id="entityName" placeholder="Entity name (try: Empresa XYZ S.A.S.)" style="width: 70%; padding: 10px;">
        <button onclick="screenEntity()" style="padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">Screen</button>
        
        <div id="result" class="result" style="display: none;"></div>
        
        <script>
        function screenEntity() {
            const entityName = document.getElementById('entityName').value;
            if (!entityName) return;
            
            fetch('/screen', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ entity_name: entityName })
            })
            .then(response => response.json())
            .then(data => {
                const resultDiv = document.getElementById('result');
                resultDiv.style.display = 'block';
                
                const riskClass = data.risk_level.toLowerCase();
                
                let html = `
                    <h2>Screening Result: ${data.entity}</h2>
                    <p><strong>Risk Score:</strong> <span class="${riskClass}">${data.risk_score}/100 (${data.risk_level})</span></p>
                    <p><strong>Screening Date:</strong> ${data.screening_date}</p>
                `;
                
                if (data.sanctions_matches.length > 0) {
                    html += `<div class="critical-alert"><strong>⚠️ DIRECT SANCTIONS MATCHES:</strong><ul>`;
                    data.sanctions_matches.forEach(match => {
                        html += `<li>${match.name} - ${match.data.lists.join(', ')} - ${match.data.reason}</li>`;
                    });
                    html += `</ul></div>`;
                }
                
                if (data.ownership_analysis.indirect_sanctions && data.ownership_analysis.indirect_sanctions.length > 0) {
                    html += `<div class="critical-alert"><strong>⚠️ INDIRECT SANCTIONS EXPOSURE (50% Rule):</strong><ul>`;
                    data.ownership_analysis.indirect_sanctions.forEach(match => {
                        html += `<li>${match.owner} (indirect control: ${match.indirect_percentage.toFixed(1)}%) - ${match.sanctions_data.lists.join(', ')}`;
                        if (match.control_chain) html += ` - Chain: ${match.control_chain}`;
                        html += `</li>`;
                    });
                    html += `</ul></div>`;
                }
                
                if (data.ownership_analysis.jurisdiction_risk === 'HIGH') {
                    html += `<div class="alert"><strong>⚠️ HIGH-RISK JURISDICTION:</strong> ${data.ownership_analysis.jurisdiction} (FATF grey list)</div>`;
                }
                
                html += `<h3>Recommendations:</h3><ul>`;
                data.recommendations.forEach(rec => {
                    html += `<li>${rec}</li>`;
                });
                html += `</ul>`;
                
                resultDiv.innerHTML = html;
            });
        }
        </script>
    </body>
    </html>
    '''

@app.route('/screen', methods=['POST'])
def screen():
    entity_name = request.json.get('entity_name', '')
    
    sanctions_matches = []
    for name, data in SANCTIONS_DB.items():
        if name.lower() in entity_name.lower():
            sanctions_matches.append({
                "name": name,
                "data": data
            })
    
    ownership_analysis = analyze_ownership(entity_name)
    risk_score = calculate_risk_score(sanctions_matches, ownership_analysis)
    
    result = {
        "entity": entity_name,
        "screening_date": "2024-05-13",
        "risk_score": risk_score,
        "risk_level": get_risk_level(risk_score),
        "sanctions_matches": sanctions_matches,
        "ownership_analysis": ownership_analysis,
        "recommendations": get_recommendations(risk_score, sanctions_matches)
    }
    
    return jsonify(result)

def analyze_ownership(entity_name):
    entity = OWNERSHIP_DATA.get(entity_name, None)
    
    if not entity:
        return {
            "status": "limited_data",
            "note": "Datos de propiedad no disponibles en fuentes públicas"
        }
    
    indirect_sanctions = []
    for owner in entity['owners']:
        if owner['name'] in SANCTIONS_DB:
            indirect_sanctions.append({
                "owner": owner['name'],
                "percentage": owner['percentage'],
                "sanctions_data": SANCTIONS_DB[owner['name']],
                "indirect_control": True
            })
    
    for owner in entity['owners']:
        owner_entity = OWNERSHIP_DATA.get(owner['name'], None)
        if owner_entity:
            for sub_owner in owner_entity['owners']:
                if sub_owner['name'] in SANCTIONS_DB:
                    indirect_percentage = owner['percentage'] * sub_owner['percentage'] / 100
                    indirect_sanctions.append({
                        "owner": sub_owner['name'],
                        "direct_entity": owner['name'],
                        "indirect_percentage": indirect_percentage,
                        "sanctions_data": SANCTIONS_DB[sub_owner['name']],
                        "indirect_control": True,
                        "control_chain": f"{owner['name']} ({owner['percentage']}%) → {sub_owner['name']} ({sub_owner['percentage']}%)"
                    })
    
    return {
        "status": "analyzed",
        "jurisdiction": entity['jurisdiction'],
        "jurisdiction_risk": "HIGH" if entity['jurisdiction'] == "Panamá" else "MEDIUM",
        "incorporation_date": entity['incorporation_date'],
        "direct_owners": entity['owners'],
        "indirect_sanctions": indirect_sanctions,
        "total_indirect_control": sum(s['indirect_percentage'] for s in indirect_sanctions)
    }

def calculate_risk_score(sanctions_matches, ownership_analysis):
    score = 0
    
    if sanctions_matches:
        score += 50
    
    if ownership_analysis.get('indirect_sanctions'):
        total_control = ownership_analysis.get('total_indirect_control', 0)
        if total_control >= 50:
            score += 30
        elif total_control > 0:
            score += 15
    
    if ownership_analysis.get('jurisdiction_risk') == 'HIGH':
        score += 10
    
    if ownership_analysis.get('status') == 'limited_data':
        score += 10
    
    return min(score, 100)

def get_risk_level(score):
    if score >= 80: return "CRITICAL"
    elif score >= 60: return "HIGH"
    elif score >= 40: return "MEDIUM"
    else: return "LOW"

def get_recommendations(score, sanctions_matches):
    if score >= 80:
        return [
            "NO proceder con relación comercial",
            "Enhanced Due Diligence requerida",
            "Escalar a Oficial de Cumplimiento Principal",
            "Considerar Reporte de Operación Sospechosa"
        ]
    elif score >= 60:
        return [
            "Enhanced Due Diligence antes de proceder",
            "Aprobación de Oficial de Cumplimiento requerida",
            "Monitoreo continuo recomendado"
        ]
    elif score >= 40:
        return [
            "Due Diligence estándar con atención a señales de alerta",
            "Revisión en 6 meses"
        ]
    else:
        return [
            "Due Diligence simplificada",
            "Próxima revisión en 12 meses"
        ]

if __name__ == '__main__':
    app.run(debug=True)
