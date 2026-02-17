import fs from 'fs';
import path from 'path';
import AdmZip from 'adm-zip';
import { XMLParser } from 'fast-xml-parser';
import { NodeHtmlMarkdown } from 'node-html-markdown';
import { program } from 'commander';

const parser = new XMLParser({
    ignoreAttributes: false,
    attributeNamePrefix: "@_"
});

const nhm = new NodeHtmlMarkdown();

program
    .version('1.0.0')
    .argument('<epub-path>', 'Path to the EPUB file')
    .option('-c, --category <category>', 'Book category', '未分类')
    .option('-t, --tags <tags>', 'Extra tags (comma separated)', '')
    .option('-o, --output <output>', 'Output directory', '../../书籍/00_待分类')
    .action(async (epubPath, options) => {
        try {
            await convertEpub(epubPath, options);
        } catch (err) {
            console.error('Error during conversion:', err.message);
        }
    });

program.parse();

async function convertEpub(epubPath, options) {
    if (!fs.existsSync(epubPath)) {
        throw new Error(`File not found: ${epubPath}`);
    }

    console.log(`Processing: ${path.basename(epubPath)}...`);
    const zip = new AdmZip(epubPath);
    const zipEntries = zip.getEntries();

    // 1. Locate container.xml to find the root OPF file
    const containerEntry = zipEntries.find(e => e.entryName === 'META-INF/container.xml');
    if (!containerEntry) throw new Error('Not a valid EPUB: Missing container.xml');
    
    const containerJson = parser.parse(containerEntry.getData().toString());
    const opfPath = containerJson.container.rootfiles.rootfile['@_full-path'];
    const rootDir = path.dirname(opfPath);

    // 2. Parse OPF for metadata and manifest
    const opfEntry = zipEntries.find(e => e.entryName === opfPath);
    const opfJson = parser.parse(opfEntry.getData().toString());
    const metadata = opfJson.package.metadata;
    const manifest = opfJson.package.manifest.item;
    const spine = opfJson.package.spine.itemref;

    let title = metadata['dc:title'];
    if (typeof title === 'object') title = title['#text'] || JSON.stringify(title);
    
    let author = metadata['dc:creator'];
    if (typeof author === 'object') author = author['#text'] || (Array.isArray(author) ? author[0]['#text'] : 'Unknown Author');

    console.log(`Title: ${title}`);
    console.log(`Author: ${author}`);

    // 3. Extract and convert chapters in spine order
    let fullMarkdown = '';
    
    const tagList = ['book'];
    if (options.tags) {
        options.tags.split(',').forEach(t => tagList.push(`book/${t.trim()}`));
    }
    
    // Frontmatter
    const escapedTitle = String(title).replace(/"/g, '\"');
    const escapedAuthor = String(author).replace(/"/g, '\"');

    fullMarkdown += `---\n`;
    fullMarkdown += `title: "${escapedTitle}"
`;
    fullMarkdown += `author: "${escapedAuthor}"
`;
    fullMarkdown += `tags: [${tagList.join(', ')}]
`;
    fullMarkdown += `category: ${options.category}
`;
    fullMarkdown += `status: 未读
`;
    fullMarkdown += `---\n\n`;
    fullMarkdown += `# ${title}\n\n`;

    const spineItems = Array.isArray(spine) ? spine : [spine];
    const manifestItems = Array.isArray(manifest) ? manifest : [manifest];

    for (const itemRef of spineItems) {
        const idref = itemRef['@_idref'];
        const item = manifestItems.find(m => m['@_id'] === idref);
        if (!item) continue;

        let href = item['@_href'];
        // Handle paths properly
        const chapterPath = path.posix.join(rootDir, href);
        const chapterEntry = zipEntries.find(e => e.entryName === chapterPath || e.entryName === decodeURIComponent(chapterPath));
        
        if (chapterEntry) {
            const html = chapterEntry.getData().toString('utf8');
            const md = nhm.translate(html);
            fullMarkdown += md + '\n\n---\n\n';
        }
    }

    // 4. Write to file
    const safeTitle = String(title).replace(/[\\/:*?"<>|]/g, '_').trim();
    const outputDir = path.resolve(path.dirname(import.meta.url.replace('file:///', '')), options.output);
    
    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
    }

    const outputPath = path.join(outputDir, `${safeTitle}.md`);
    fs.writeFileSync(outputPath, fullMarkdown);
    
    console.log(`Success! Saved to: ${outputPath}`);
}
