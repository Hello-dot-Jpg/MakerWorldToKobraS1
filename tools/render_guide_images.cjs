// Optional local visual QA: render the SVG guide drawings, never capture a desktop.
// Usage: node tools/render_guide_images.cjs /path/to/sharp output-folder
const fs = require('node:fs');
const path = require('node:path');
const sharp = require(path.resolve(process.argv[2]));
const output = path.resolve(process.argv[3]);
fs.mkdirSync(output, { recursive: true });
const images = path.resolve(__dirname, '../docs/images');
(async () => {
  for (const file of fs.readdirSync(images).filter(name => name.endsWith('.svg'))) {
    const destination = path.join(output, file.replace(/\.svg$/, '.png'));
    if (fs.existsSync(destination)) throw new Error(`Refusing to overwrite ${destination}`);
    await sharp(path.join(images, file)).png().toFile(destination);
  }
  console.log(output);
})().catch(error => { console.error(error.message); process.exitCode = 1; });
