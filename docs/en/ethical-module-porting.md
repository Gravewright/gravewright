# How to port modules to Gravewright ethically

Porting a module starts with identifying which parts you are authorized to adapt. Its features can then be mapped to Gravewright's domains. The code license, content license and permissions to use trademarks must be examined separately.

## 1. How to read a module's license

Examine the exact version you intend to port. Look for files such as `LICENSE`, `COPYING`, `NOTICE`, the README, file headers and the terms accompanying images, fonts, audio and content collections. The manifest's license field is an indication; by itself, it does not resolve exceptions or materials with their own licensing terms.

For each part, answer:

| Question | What to check |
| --- | --- |
| Who can authorize its use? | The rights holder for that code or content. The module maintainer may not control the rights to images or game material. |
| What does the license cover? | The entire package, code only, specific files or an expressly identified selection. |
| May I modify it? | Permission to adapt, translate and create derivative versions. |
| May I distribute the adaptation? | Modifying something for personal use and providing copies to others are different situations. |
| May I charge for it? | Commercial permission and any restrictions on the context of use. Being free of charge does not waive the other conditions. |
| What must I preserve or provide? | Credits, license text, notices, identification of changes and source code, as required by the applicable terms. |
| Are there additional limits? | License version, exceptions, excluded materials and authorizations restricted to particular uses or environments. |

Record the source, version and terms you find. If there is a contradiction or authorization is missing for a part, leave that part out of the port until you clarify it with the rights holder.

A public repository or a free download is not equivalent to a license to adapt and redistribute. In the absence of a license, do not assume those permissions. [Reference on the absence of a license](https://choosealicense.com/no-permission/).

## 2. License types and what to look for

This table guides your reading; the actual conditions are those of the text and version applicable to the material.

| Type | Consequence for the port |
| --- | --- |
| Permissive, such as MIT and BSD | Generally allow adaptation and redistribution, including commercially, while preserving the required notices. Check the variant; similar names can have different conditions. |
| Apache-2.0 | Allows adaptation and distribution subject to conditions such as preserving the license, identifying modified files and reproducing relevant `NOTICE` notices, where present. Includes patent provisions and does not grant general authorization to use trademarks. |
| Strong copyleft, such as GPL | Allows porting, including commercially. When distributing a covered derivative work, requires compliance with copyleft and making the corresponding source code available under the license's conditions. Check the version, exceptions and compatibility of the combined parts. |
| AGPL | In addition to copyleft, contains a specific obligation to offer corresponding source code to users interacting remotely with a modified version, under the license's conditions. |
| File-level copyleft, such as MPL-2.0 | Covered files and their modifications retain MPL obligations when distributed. Independent files may have another license; moving covered code into a new file does not remove its obligations. |
| Proprietary or custom license | Read the express permissions. Buying or receiving access to a module does not, by itself, establish authorization to distribute a port. |
| Dual licensing | Check whether you can choose one of the licenses or whether different parts require cumulative compliance with multiple conditions. |
| No identified license | Request authorization to reuse the material; do not treat silence as permission. |

References: [license comparison](https://choosealicense.com/appendix/), [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0), [GPL-3.0](https://choosealicense.com/licenses/gpl-3.0/), [AGPL-3.0](https://choosealicense.com/licenses/agpl-3.0/) and [MPL-2.0 explanation](https://www.mozilla.org/en-US/MPL/2.0/FAQ/).

### Content licenses

Text, illustrations and other resources may have terms different from those of the code. For Creative Commons licenses, examine the elements present:

| Element | What it means for the analysis |
| --- | --- |
| BY — attribution | Provide the required credits, identify the license and indicate changes where applicable. |
| SA — share alike | When sharing an adaptation, use the same license or a license accepted as compatible. |
| NC — noncommercial | Commercial use falls outside the authorization. The analysis considers purpose and context; the file being free of charge is not enough. |
| ND — no derivatives | Does not authorize sharing adapted material. A simple format change is not automatically an adaptation, but translating or transforming the content requires a separate analysis. |

The elements combine: a license with BY, NC and ND requires observing all three. Also check the version. [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) and [CC BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/).

## 3. What can and cannot be ported

Make the decision component by component, rather than relying only on the module's name or main license.

| Situation | Decision |
| --- | --- |
| Code under a license authorizing adaptation and distribution | It can be ported while meeting its conditions and those of the dependencies used. |
| Open-source code accompanied by images with reserved rights | Authorization for the code does not automatically cover the images. Exclude them or obtain separate authorization. |
| Content expressly released for adaptation and redistribution | It can be included within the authorized scope, with the required notices and conditions. |
| Authorization only for personal use or a specific environment | Do not extend that authorization to distribution in Gravewright. Request permission covering the intended use. |
| A book, adventure, map or collection purchased by the user | The purchase does not establish authorization to incorporate that material into a distributed module. Check the granted rights separately. |
| Material without a license or with uncertain ownership | Do not include it until the necessary authorization is clarified. |
| Resources you created | They can be used insofar as you hold the necessary rights; check any contributions and incorporated materials. |

For example, a module may contain permissively licensed code, an artist's icons and descriptions licensed by a publisher. Porting the code may be authorized while porting the icons and descriptions depends on other permissions. The main license does not turn the entire package into material freely available for reuse.

## 4. Intellectual property considerations

**Separate functionality from expression.** Describing that a function calculates a roll helps map its behavior. Copying its implementation, text or presentation involves materials that need examination. Rewriting code does not automatically release incorporated content or resolve every intellectual property issue.

**Do not use conversion as a justification.** Translating descriptions, extracting text from a document or converting a collection into another format does not create authorization to redistribute it. Check the terms of the source content.

**Treat trademarks and visual identity separately.** Do not assume a software license allows you to reuse logos or present the port as official. Preserve credits without suggesting a nonexistent partnership, approval or endorsement. Apache-2.0 itself distinguishes the code license from trademark rights. [Section 6 of Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0).

**Credit does not replace permission.** Identifying the author is required by various licenses, but does not authorize a use that their terms do not allow. Keep specific authorizations and respect exactly the material and conditions they cover.

**Gravewright's license does not change the source license.** The permission for independent modules allows them to use other licenses, including proprietary ones, within its scope. It does not grant rights to third-party code or resources, or remove obligations concerning copied or adapted core code. See the [licensing policy](../../LICENSING.md) and the [normative text of the independent-module permission](../../LICENSE-EXCEPTION).

## 5. How to map features to domains

After identifying what is authorized, describe each feature in terms of what it does and the data it uses. Then find the responsible domain in Gravewright. The source module's names and internal organization do not need to be reproduced.

| Feature | Gravewright domain | How to interpret the mapping |
| --- | --- | --- |
| Characters, creatures and sheet data | `actors` | The character is a native actor. The sheet's specific presentation corresponds to the `actor.sheet` surface. |
| Character representation on the map, position, vision and conditions | `tokens` | Distinguish actor data from the data of its representation in a scene. The corresponding sheet surface is `token.sheet`. |
| Inventory, equipment, powers, ancestries, hindrances and addable abilities | `items` + `actors` | Model components as items; the sheet retains the character-owned association or copy data, according to the rule. Drag and drop connects the item library to the sheet. |
| Editing an item's specific data | `items` | Use the native item as the document and `item.sheet` as the presentation surface. |
| Maps and scene objects | `maps` | Relate resources to maps and scene operations available in the contract. |
| Notes, documents, adventures and shared information | `journals` | Map the document and its access, including GM-only content. |
| Participants, initiative, rounds and turns | `combat` | The domain controls combat state; the specific rule determines how to calculate values. |
| Decks, drawing, discarding and shuffling | `cards` | Separate deck operations from the rules that interpret the drawn card. |
| Tracks, playlists and positional sounds | `audio` | Map playback behavior; authorization to distribute audio remains independent. |
| Reusable document libraries | `compendiums` | Map the collection and its documents, including the rights and permissions of each piece of content. |

Domains handle data and operations. Surfaces such as `actor.sheet` and `item.sheet` handle presentation. A custom sheet does not imply creating another character directory; custom item types do not imply creating another global inventory. Use the corresponding native structure.

For each feature, record:

| Field | Example |
| --- | --- |
| Behavior | Add equipment to a character and account for its modifier. |
| Material involved | Calculation logic, equipment data, description and icon. |
| Identified rights | License and authorization for each part, including exclusions. |
| Domains | `items` for equipment; `actors` for character data. |
| Presentation | `item.sheet` for editing; `actor.sheet` for displaying equipment on the sheet. |
| Port boundary | Implement the authorized behavior and exclude any description or icon without permission. |

A feature may involve several domains. A card that changes initiative combines `cards` and `combat`; a power applied to a creature may involve `items`, `actors` and `tokens`. If the contract has no corresponding operation, record the gap rather than assuming every behavior of the source is already supported.

Available domains and operations are listed in the [API documentation](api.md); surfaces are described in the [module documentation](modules.md). This mapping must preserve native access permissions and distinguish shared data from data belonging to each character or scene.
