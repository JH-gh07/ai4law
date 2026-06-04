# “SCC审查”测试案例及预期输出

“SCC审查”测试案例及预期输出

测试案例一：C2C模块 - 缺失补充措施与第三国法律评估

场景：法国巴黎的“欧陆时尚电商公司”（EU Fashion E-commerce SAS，数据输出方）计划将其欧盟客户的基本联系信息（姓名、邮箱、地址）和订单历史数据传输给其在英国的关联公司“英伦营销分析有限公司”（UK Marketing Analytics Ltd，数据输入方），用于市场趋势分析和个性化营销。英国已获得欧盟充分性认定，但数据输入方将使用位于美国的云服务提供商（AWS）进行数据处理和存储。

植入的风险点：
	•	缺失第三国法律评估：双方仅签署了SCC，但未按照EDPB建议01/2020进行“传输影响评估”（TIA），特别是未评估数据经英国传输至美国AWS服务器所面临的美国法律（如《云法案》、FISA 702）可能带来的访问风险。
	•	缺失补充措施：SCC附件中未约定任何技术性或组织性补充措施（如加密、假名化、合同承诺）来应对已识别的美国法律风险。
	•	数据类别描述模糊：“订单历史数据”可能包含支付信息等敏感数据，但未在附录中明确分类。

提交审查的SCC文档全文（关键部分节选）：
Plain Text STANDARD CONTRACTUAL CLAUSES ...  **Clause 1: Purpose and scope** ... **Clause 2: Effect and invariability of the Clauses** ... **Clause 3: Third-party beneficiaries** ... **Clause 4: Interpretation** ... **Clause 5: Hierarchy** ... **Clause 6: Description of the transfer(s)** The details of the transfer(s), and in particular the categories of personal data that are transferred and the purpose(s) for which they are transferred, are specified in Annex I.B.  **Clause 7 – Optional: Docking clause** Not used.  **Clause 8: Data protection safeguards** The data exporter warrants that it has used reasonable efforts to determine that the data importer is able, through the implementation of appropriate technical and organisational measures, to satisfy its obligations under these Clauses. ... **Clause 9: Use of sub-processors** Not applicable for Module One. ... **Clause 10: Data subject rights** ... **Clause 11: Redress** ... **Clause 12: Liability** ... **Clause 13: Supervision** ... **Clause 14: Local laws and practices affecting compliance with the Clauses** (a) The Parties warrant that they have no reason to believe that the laws and practices in the third country of destination applicable to the processing of the personal data by the data importer, including any requirements to disclose personal data or measures authorising access by public authorities, prevent the data importer from fulfilling its obligations under these Clauses. This is based on the understanding that laws and practices that respect the essence of the fundamental rights and freedoms and do not exceed what is necessary and proportionate in a democratic society to safeguard one of the objectives listed in Article 23(1) of Regulation (EU) 2016/679, are not in contradiction with these Clauses. (b) The Parties declare that in providing the warranty in paragraph (a), they have taken due account in particular of the following elements:     (i) the specific circumstances of the transfer, including the length of the processing chain, the number of actors involved and the transmission channels used; intended onward transfers; the type of recipient; the purpose of processing; the categories and format of the personal data; the economic sector in which the transfer occurs; the storage location of the data transferred;     (ii) the laws and practices of the third country of destination– including those requiring the disclosure of data to public authorities or authorising access by such authorities – relevant in light of the specific circumstances of the transfer, and the applicable limitations and safeguards;     (iii) any relevant contractual, technical or organisational safeguards put in place to supplement the safeguards under these Clauses, including measures applied during transmission and to the processing of the personal data in the country of destination. (c) The data importer agrees to document the assessment made under paragraph (b) as well as any suitable safeguards identified and provide it to the data exporter on request. The data importer agrees to make the assessment available to the competent supervisory authority on request. ... **Clause 15: Obligations of the data importer in case of access by public authorities** ... **Clause 16: Non-compliance with the Clauses and termination** ... **Clause 17: Governing law** ... **Clause 18: Choice of forum and jurisdiction** ...  **ANNEX I**  A. LIST OF PARTIES Data exporter(s): [Identity and contact details of the data exporter(s) and, where applicable, of its/their data protection officer and/or representative in the European Union]    Name: EU Fashion E-commerce SAS    Address: 123 Avenue des Champs-Élysées, 75008 Paris, France    Contact person’s name, position and contact details: Marie Dubois, DPO, dpo@eufashion.fr    Activities relevant to the data transferred under these Clauses: E-commerce retail    Signature and date: (电子签名) 2025-10-26    Role (controller/processor): Controller  Data importer(s): [Identity and contact details of the data importer(s) and, where applicable, of its/their data protection officer and/or representative in the European Union]    Name: UK Marketing Analytics Ltd    Address: 456 Oxford Street, London, W1C 1DJ, United Kingdom    Contact person’s name, position and contact details: John Smith, Data Protection Manager, privacy@ukmarketing.co.uk    Activities relevant to the data transferred under these Clauses: Data analytics for marketing purposes    Signature and date: (电子签名) 2025-10-26    Role (controller/processor): Controller  B. DESCRIPTION OF TRANSFER Categories of data subjects whose personal data is transferred:    Customers of the data exporter (EU-based individuals).  Categories of personal data transferred:    Contact information (name, email address, delivery address).    Order history data (products purchased, purchase dates, order values).  Sensitive data transferred (if applicable) and applied restrictions or safeguards:    Not applicable. No sensitive data is transferred.  The frequency of the transfer (e.g. whether the data is transferred on a one-off or continuous basis):    Continuous, on a daily basis.  Nature of the processing:    Storage, analysis, profiling for marketing purposes.  Purpose(s) of the data transfer and further processing:    Market trend analysis, customer segmentation, and personalized marketing communication by the data importer.  The period for which the personal data will be retained, or, if that is not possible, the criteria used to determine that period:    Personal data will be retained for 3 years from the last customer interaction, unless a longer retention period is required by applicable law.  For transfers to (sub-) processors, also specify subject matter, nature and duration of the processing:    Not applicable for Module One.  C. COMPETENT SUPERVISORY AUTHORITY    The competent supervisory authority shall be the French data protection authority (CNIL).  **ANNEX II - TECHNICAL AND ORGANISATIONAL MEASURES** [The data importer shall implement the following measures:]    - Encryption of personal data in transit using TLS 1.2 or higher.    - Encryption of personal data at rest using AES-256.    - Access controls based on the principle of least privilege.    - Regular security awareness training for employees.    (注：此处仅列出了基本安全措施，未提及任何针对美国法律风险的补充措施，如额外加密、合同承诺等)  **ANNEX III – LIST OF SUB-PROCESSORS** Not applicable for Module One.

预期输出（《SCC合规审查报告》核心发现）：
	•	总体合规评级：高风险。本SCC文档在形式上采用了正确的模块（Module One: C2C），但完全缺失了“Schrems II”判决和EDPB建议01/2020所要求的核心合规步骤：对数据最终存储地（美国）的法律环境进行影响评估，并实施有效的补充措施。仅依赖SCC本身不足以构成合法的传输基础。
	•	条款级审查发现（示例）：
◦   定位：Clause 14(a) & (b), Annex I.B, Annex II.

◦   问题类型：与实践不一致/重大遗漏。

◦   风险分析：Clause 14要求双方保证已考虑第三国法律风险并采取了补充措施。然而，Annex I.B未说明数据将经由英国最终存储于美国AWS服务器。Annex II仅列出了通用安全措施，未包含任何针对美国《云法案》(CLOUD Act)等法律可能允许政府访问数据的补充措施。双方显然未进行必要的“传输影响评估”（TIA）。根据“Schrems II”案，若数据输入方所在国（此处为数据实际存储国美国）的法律妨碍其遵守SCC，则传输非法。

◦   法规/标准依据：GDPR第46条；欧盟法院“Schrems II”案判决 (C-311/18)；EDPB建议01/2020。

◦   修改建议：

    1.  在Annex I.B中明确说明数据的最终存储/处理地点（美国AWS）。
    2.  双方必须根据EDPB建议01/2020进行正式的传输影响评估，评估美国法律对数据传输的影响，并将评估报告作为合同附件。
    3.  在Annex II中增加针对性的补充措施，例如：合同措施：要求AWS（作为子处理者）提供具有约束力的承诺，抵抗非法的数据访问请求；技术措施：对传输至美国的数据实施端到端加密，且密钥仅由数据输出方（欧盟实体）持有。

测试案例二：C2P模块 - 高风险第三国且条款被不当修改

场景：德国柏林的“健康研究所有限公司”（Gesundheitsforschung GmbH，数据输出方，控制者）委托印度班加罗尔的“数据洞察解决方案公司”（Data Insights Solutions Pvt. Ltd.，数据输入方，处理者）进行医疗研究数据的统计分析。传输的数据包含匿名的患者健康数据（但根据GDPR仍属特殊类别数据）。双方签署了SCC Module Two (C2P)。

植入的风险点：
	•	高风险第三国法律环境：印度尚未获得欧盟充分性认定，且其《信息技术法》及修订案赋予政府广泛的数据访问权，与EDPB建议中关注的法律特征相符。
	•	SCC关键条款被修改：双方在附件中修改了Clause 15关于政府访问请求的通知义务，将通知时限从“尽可能及时”改为“在法律允许的范围内尽快”，并删除了提供聚合信息的要求。
	•	数据敏感性描述不足：Annex I.B中将“患者健康数据”描述为“非敏感”，与GDPR定义冲突。
	•	子处理者授权机制不明确：Clause 9关于子处理者的约定中，未明确数据输出方对子处理者名单的具体书面授权方式。

提交审查的SCC文档全文（关键问题部分节选）：
Plain Text **Clause 9: Use of sub-processors** ... (g) The data importer shall submit any planned changes to its list of sub-processors to the data exporter via email. If the data exporter does not object in writing within fifteen (15) business days of receipt of the notification, the data importer may engage the new sub-processor. (注：此条款符合SCC范本，但未在附件中明确列出子处理者或授权机制细节)  **Clause 14: Local laws and practices affecting compliance with the Clauses** ...(a) & (b) 标准文本... (c) The data importer agrees to document the assessment made under paragraph (b) as well as any suitable safeguards identified and provide it to the data exporter **only upon a specific, justified request**. (注：此处修改了范本中“on request”的表述，增加了限制条件)  **Clause 15: Obligations of the data importer in case of access by public authorities** (a) The data importer agrees to notify the data exporter and, where possible, the data subject (if necessary with the help of the data exporter) **as soon as legally permissible** if it:     (i) receives a legally binding request from a public authority, including judicial authorities, under the laws of the country of destination for the disclosure of personal data transferred pursuant to these Clauses; or     (ii) becomes aware of any direct access by public authorities to personal data transferred pursuant to these Clauses in accordance with the laws of the country of destination.     The data importer shall also provide the data exporter, **at its discretion**, with relevant information about the request. (注：此处严重削弱了通知义务) (b) ... (c) ... (d) The data importer agrees to preserve the information required to be provided pursuant to paragraph (a) for the duration of the contract and make it available to the competent supervisory authority on request. (e) Paragraphs (a) to (c) are without prejudice to the obligation of the data importer pursuant to Clause 14(e) and Clause 16 to inform the data exporter promptly where it is unable to comply with these Clauses.  **ANNEX I** B. DESCRIPTION OF TRANSFER ... Categories of personal data transferred:    Patient unique study identifier (pseudonymised), age group, gender, diagnostic codes, treatment codes, laboratory test results (anonymised).  Sensitive data transferred (if applicable) and applied restrictions or safeguards:    **Not applicable. The data is anonymised for research purposes and does not constitute special categories of data.** (注：错误描述！根据GDPR，用于研究的健康数据即使匿名化，在特定上下文中仍可能被视为特殊类别数据处理，需要额外保护) ...

预期输出（《SCC合规审查报告》核心发现）：
	•	总体合规评级：高风险。本SCC文档在关键条款（Clause 15）上做出了与标准范本相悖且削弱数据主体保护的修改，违反了SCC不可更改的核心原则。同时，对传输特殊类别健康数据的风险认识不足，且未针对印度高风险法律环境约定充分的补充措施。
	•	条款级审查发现（示例）：
◦   定位：Clause 15(a).

◦   问题类型：与法规冲突/无效修改。

◦   风险分析：将通知义务修改为“as soon as legally permissible”并赋予数据输入方提供信息的自由裁量权，严重削弱了SCC范本旨在确保的透明度和问责制。根据欧盟委员会实施决定(EU) 2021/914的序言(3)，对SCC的任何补充条款不得“直接或间接与标准合同条款相抵触”。此修改与Clause 15旨在确保数据输出方和数据主体能及时知晓政府访问请求的核心目的相抵触，可能使该条款整体无效。

◦   法规/标准依据：欧盟委员会实施决定(EU) 2021/914序言(3)；Clause 15标准文本。

◦   修改建议：必须将Clause 15(a)恢复为标准文本：“...if it: receives a legally binding request... The data importer shall also provide the data exporter with all relevant information about the request, including the nature of the request, the data requested, and the requesting authority.”

◦   定位：Annex I.B, “Sensitive data transferred”.

◦   问题类型：定义错误/风险识别不足。

◦   风险分析：声明传输的数据“不构成特殊类别数据”是错误的。用于研究的健康数据（即使是匿名化的）在GDPR下通常被视为特殊类别数据（第9条），需要更高水平的保护。此错误描述可能导致双方未能实施GDPR第9条要求的适当保障措施（如明确同意或研究豁免条件），并影响传输影响评估的准确性。

◦   法规/标准依据：GDPR第9条；Recital 159。

◦   修改建议：更正为：“Yes. Health data for research purposes, even anonymised, is considered special category data under Article 9 GDPR. The transfer is based on Article 9(2)(j) GDPR (archiving, scientific research). Additional safeguards applied: [描述额外的技术组织措施，如强加密、严格访问控制、数据处理协议等]”。


测试案例三：多方加入与模块选择错误

场景：荷兰的云服务提供商“橙子云BV”（Orange Cloud BV，作为数据输出方和初始处理者）代表其客户“北欧零售集团”（Nordic Retail Group，实际控制者）处理客户数据。橙子云BV计划将部分客户支持工单数据（含客户姓名、问题描述）转委托给位于塞尔维亚（非充分性认定国家）的子处理者“巴尔干IT支持公司”（Balkan IT Support DOO）。三方拟通过SCC的“加入条款”（Docking Clause）来建立合规框架。

植入的风险点：
	•	模块选择错误：实际关系是：北欧零售集团（C） -> 橙子云BV（P） -> 巴尔干IT支持公司（Sub-P）。这应使用Module Three: Processor to Processor (P2P)。但文档中错误地选择了Module Two: Controller to Processor (C2P)，并将“橙子云BV”同时设为数据输出方和数据输入方，逻辑混乱。
	•	加入方信息缺失：Annex I.A中，“北欧零售集团”作为实际控制者和数据输出方的上游方，其信息未被完整填写，仅写了“见主服务协议”，导致责任主体不明确。
	•	子处理者授权链不完整：未清晰展示从控制者到处理者再到子处理者的完整授权链条，Clause 9的机制未与附件信息联动。

提交审查的SCC文档全文（关键问题部分节选）：
Plain Text **MODULE TWO: Transfer controller to processor** (注：错误的选择！) **Clause 7: Docking clause**     (a) An entity that is not a Party to these Clauses may, with the agreement of the Parties, accede to these Clauses at any time, either as a data exporter or as a data importer, by completing the Annexes and signing Annex I.A.     (b) Once it has completed the Annexes and signed Annex I.A, the acceding entity shall become a Party to these Clauses and have the rights and obligations of a data exporter or data importer in accordance with its designation in Annex I.A.     (c) The acceding entity shall have no rights or obligations arising under these Clauses from the period prior to becoming a Party.  **ANNEX I** A. LIST OF PARTIES **Data exporter(s):**    Name: Orange Cloud BV    Address: Cloudweg 100, 1011 Amsterdam, Netherlands    Contact details: privacy@orangecloud.nl    Activities relevant to the data transferred: Provision of cloud infrastructure and support services.    Signature and date: (Signed) 2025-11-15    Role (controller/processor): **Processor** (注：在Module Two中，数据输出方应是Controller，此处矛盾)  **Data importer(s):**    Name: Orange Cloud BV (acting on behalf of its customer, Nordic Retail Group) (注：逻辑错误，数据输入方不应是自身)    Address: Cloudweg 100, 1011 Amsterdam, Netherlands    Contact details: privacy@orangecloud.nl    Activities relevant to the data transferred: Sub-processing of customer support ticket data.    Signature and date: (Signed) 2025-11-15    Role (controller/processor): **Processor**  **Acceding Party (as data exporter):**    Name: **See Master Services Agreement between Orange Cloud BV and Nordic Retail Group.** (注：信息缺失！)    Address: [Not specified]    Contact details: [Not specified]    Activities relevant to the data transferred: [Not specified]    Signature and date: [Not provided]    Role (controller/processor): Controller  B. DESCRIPTION OF TRANSFER ... For transfers to (sub-) processors, also specify subject matter, nature and duration of the processing:    Subject matter: Processing of customer support ticket data.    Nature of the processing: Storage, access, troubleshooting, and analysis for service improvement.    Duration of the processing: For the duration of the main service agreement plus 30 days for data deletion.

预期输出（《SCC合规审查报告》核心发现）：
	•	总体合规评级：高风险。本SCC文档存在根本性的模块选择错误和关键方信息缺失，导致法律关系混乱，可能使得整个SCC无法有效建立合法的数据传输框架。
	•	条款级审查发现（示例）：
◦   定位：文档标题及整体结构。

◦   问题类型：与实践不一致/模块选择错误。

◦   风险分析：传输链是：控制者（北欧零售集团）-> 处理者（橙子云BV）-> 子处理者（巴尔干IT支持公司）。这应使用 Module Three (Processor to Processor)。错误地使用Module Two (Controller to Processor) 会导致角色定义混乱（如将橙子云BV既作为输出方又作为输入方），且无法正确反映GDPR第28条下处理者与子处理者之间的合同义务要求。错误的模块选择可能使SCC整体无效。

◦   法规/标准依据：欧盟委员会实施决定(EU) 2021/914附件，Module Three适用范围；GDPR第28(4)条。

◦   修改建议：必须重新采用 Module Three: Transfer processor to processor。各方角色应调整为：数据输出方：橙子云BV（处理者）；数据输入方：巴尔干IT支持公司（子处理者）。控制者（北欧零售集团）的信息应在Annex I中明确列出，或通过引用主协议明确其作为“数据输出方指示方”的身份。

◦   定位：Annex I.A, “Acceding Party”信息。

◦   问题类型：缺失条款/信息不完整。

◦   风险分析：“加入方”信息仅引用外部文件“见主服务协议”，未在SCC中明确其名称、地址、联系方式和相关活动。这违反了SCC作为自包含文件的要求，使得数据主体的第三方受益人权利无法有效行使，也导致监管机构无法明确识别最终责任方。

◦   法规/标准依据：Clause 3 (第三方受益人权利)；Clause 13 (监管)。

◦   修改建议：必须在Annex I.A中完整填写“加入方”（即实际控制者北欧零售集团）的所有详细信息，包括完整的名称、地址、联系人及角色。可以注明“其作为与数据输出方（橙子云BV）签订数据处理协议的控制者”。
