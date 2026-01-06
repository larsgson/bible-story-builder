import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function findDataFiles(dir, baseDir, results = []) {
  const files = fs.readdirSync(dir);
  
  for (const file of files) {
    const filePath = path.join(dir, file);
    const stat = fs.statSync(filePath);
    
    if (stat.isDirectory()) {
      findDataFiles(filePath, baseDir, results);
    } else if (file === 'data.json') {
      // Get relative path from baseDir
      const relativePath = path.relative(baseDir, filePath);
      // Parse the path: testament/category/langCode/distinctId/data.json
      const parts = relativePath.split(path.sep);
      if (parts.length === 5) {
        const [testament, category, langCode, distinctId] = parts;
        results.push({
          testament,
          category,
          langCode,
          distinctId,
          path: relativePath.replace(/\\/g, '/')
        });
      }
    }
  }
  
  return results;
}

const baseDir = path.join(__dirname, 'public', 'ALL-langs-data');
const dataFiles = findDataFiles(baseDir, baseDir);

// Build a structured index
const index = {
  metadata: {
    generatedAt: new Date().toISOString(),
    totalFiles: dataFiles.length
  },
  files: {}
};

for (const file of dataFiles) {
  const { testament, category, langCode, distinctId } = file;
  
  if (!index.files[testament]) {
    index.files[testament] = {};
  }
  if (!index.files[testament][category]) {
    index.files[testament][category] = {};
  }
  if (!index.files[testament][category][langCode]) {
    index.files[testament][category][langCode] = [];
  }
  
  index.files[testament][category][langCode].push(distinctId);
}

const outputPath = path.join(__dirname, 'public', 'ALL-langs-data', 'manifest.json');
fs.writeFileSync(outputPath, JSON.stringify(index, null, 2));

console.log(`Manifest created with ${dataFiles.length} files`);
console.log(`Output: ${outputPath}`);
