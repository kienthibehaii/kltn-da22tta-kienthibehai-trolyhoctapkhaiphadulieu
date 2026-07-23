const fs = require('fs');
const path = require('path');

function walkDir(dir, callback) {
  fs.readdirSync(dir).forEach(f => {
    let dirPath = path.join(dir, f);
    let isDirectory = fs.statSync(dirPath).isDirectory();
    isDirectory ? walkDir(dirPath, callback) : callback(path.join(dir, f));
  });
}

walkDir('./src', function(filePath) {
  if (filePath.endsWith('.tsx') || filePath.endsWith('.css')) {
    let content = fs.readFileSync(filePath, 'utf8');
    let original = content;
    // Thay đổi class Tailwind từ emerald/teal sang indigo/violet
    content = content.replace(/emerald/g, 'indigo');
    content = content.replace(/teal/g, 'violet');
    
    // Thay đổi mã màu hex trong index.css
    if (filePath.endsWith('index.css')) {
        content = content.replace(/linear-gradient\(135deg, #f0fdf4 0%, #f8fafc 50%, #f1f5f9 100%\)/g, 'linear-gradient(135deg, #f3f0f8 0%, #fbf8ff 50%, #f5f2fa 100%)');
        content = content.replace(/linear-gradient\(135deg, #10b981, #059669\)/g, 'linear-gradient(135deg, #6366f1, #4f46e5)');
        content = content.replace(/rgba\(16, 185, 129, 0.3\)/g, 'rgba(79, 70, 229, 0.3)');
    }

    if (content !== original) {
      fs.writeFileSync(filePath, content, 'utf8');
      console.log('Updated', filePath);
    }
  }
});
