/**
 * AI-BS Sovereign Data Extraction Engine
 * Exports all Cloud Firestore collections and documents directly into structured local JSON files.
 */

const fs = require('fs');
const path = require('path');
const admin = require('firebase-admin');

// Ensure output directory exists
const outputDir = path.join(__dirname, '..', 'saved_data', 'migration_exports');
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

console.log('🚀 Initializing Firebase Admin SDK Extraction Protocol...');

// Initialize with default credentials or service account if present
try {
  if (process.env.GOOGLE_APPLICATION_CREDENTIALS && fs.existsSync(process.env.GOOGLE_APPLICATION_CREDENTIALS)) {
    const serviceAccount = require(process.env.GOOGLE_APPLICATION_CREDENTIALS);
    admin.initializeApp({
      credential: admin.credential.cert(serviceAccount)
    });
  } else {
    admin.initializeApp({
      projectId: 'ai-bs-dashboard'
    });
  }
} catch (e) {
  console.log('⚠️ Notice: Standard initialized admin context active.');
}

const db = admin.firestore();

// Target collections to extract
const TARGET_COLLECTIONS = [
  'clients',
  'tasks',
  'inventory',
  'chat_messages',
  'beo_contracts',
  'osint_vaults',
  'knowledge_base',
  'system_logs',
  'users'
];

async function exportAllCollections() {
  const exportData = {
    exported_at: new Date().toISOString(),
    source_project: 'ai-bs-dashboard',
    collections: {}
  };

  console.log('📦 Extracting collections from Cloud Firestore...');

  for (const collectionName of TARGET_COLLECTIONS) {
    try {
      console.log(`  └─ Extracting collection: ${collectionName}...`);
      const snapshot = await db.collection(collectionName).get();
      
      const docs = [];
      snapshot.forEach(doc => {
        docs.push({
          id: doc.id,
          ...doc.data()
        });
      });

      exportData.collections[collectionName] = docs;
      console.log(`     ✅ Extracted ${docs.length} documents from ${collectionName}`);
    } catch (err) {
      console.warn(`     ⚠️ Skipping ${collectionName}: ${err.message}`);
      exportData.collections[collectionName] = [];
    }
  }

  const outputPath = path.join(outputDir, 'firestore_dump.json');
  fs.writeFileSync(outputPath, JSON.stringify(exportData, null, 2), 'utf-8');
  
  console.log(`\n🎉 Extraction Complete! Data saved to: ${outputPath}`);
  return exportData;
}

if (require.main === module) {
  exportAllCollections().catch(err => {
    console.error('❌ Extraction Error:', err);
  });
}

module.exports = { exportAllCollections };
