import os
import csv
import re
from datetime import datetime
import json
from collections import defaultdict


class InformationExtractionSystem:
    def __init__(self, articles_dir='articles', metadata_file='metadata.csv'):
        self.articles_dir = articles_dir
        self.metadata_file = metadata_file
        self.documents = {}
        self.metadata = {}
        self.extracted_info = defaultdict(list)

        # 定义要抽取的信息点
        self.extraction_patterns = {
            'money_amounts': {
                'pattern': r'(?:\$|USD\s*|US\$\s*)[\d,]+(?:\.\d{1,2})?\s*(?:billion|million|thousand|bn|mn|m|k|B|M|K)?(?:\s+dollars?)?|\b\d+(?:\.\d{1,2})?\s*(?:billion|million|thousand)\s+(?:dollars?|USD|pounds?|GBP|euros?|EUR)|(?:£|GBP\s*)[\d,]+(?:\.\d{1,2})?\s*(?:billion|million|thousand|bn|mn|m|k)?|(?:€|EUR\s*)[\d,]+(?:\.\d{1,2})?\s*(?:billion|million|thousand|bn|mn|m|k)?',
                'description': '金额信息'
            },
            'percentages': {
                'pattern': r'\b\d+(?:\.\d{1,2})?\s*(?:percent|%)',
                'description': '百分比数据'
            },
            'dates': {
                'pattern': r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}|\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\b\d{4}[-/]\d{1,2}[-/]\d{1,2}',
                'description': '日期信息'
            },
            'organizations': {
                'pattern': r'\b(?:[A-Z][a-z]+\s+)*(?:Corporation|Corp|Inc|Company|Co|Ltd|Limited|Group|Bank|University|Institute|Agency|Department|Ministry|Commission|Committee|Council|Association|Organization|Foundation|Fund|Trust|Partners|LLC|LLP|Plc)\b',
                'description': '组织机构'
            },
            'quoted_text': {
                'pattern': r'"([^"]+)"',
                'description': '引用内容'
            },
            'email_addresses': {
                'pattern': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                'description': '电子邮件地址'
            },
            'numbers_with_units': {
                'pattern': r'\b\d+(?:\.\d+)?\s*(?:GB|MB|KB|TB|meters?|km|miles?|kg|g|tons?|hours?|minutes?|seconds?|days?|weeks?|months?|years?)\b',
                'description': '带单位的数值'
            }
        }

    def load_documents(self):
        """加载文档和元数据"""
        print("正在加载文档...")

        # 加载元数据
        import chardet
        with open(self.metadata_file, 'rb') as f:
            raw_data = f.read()
            encoding = chardet.detect(raw_data)['encoding']

        with open(self.metadata_file, 'r', encoding=encoding) as f:
            reader = csv.DictReader(f)
            for row in reader:
                doc_id = int(row['id'])
                self.metadata[doc_id] = {
                    'title': row['title'],
                    'filename': row['filename'],
                    'url': row['url'],
                    'date': row['date']
                }

        # 加载文档内容
        loaded_count = 0
        for doc_id, meta in self.metadata.items():
            filepath = os.path.join(self.articles_dir, meta['filename'])
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.documents[doc_id] = f.read()
                loaded_count += 1

                # 只加载前120篇文档
                if loaded_count >= 120:
                    break

        print(f"已加载 {loaded_count} 篇文档")

    def clean_money_amount(self, amount_str):
        """清理和标准化金额格式"""
        # 移除多余的空格
        amount_str = ' '.join(amount_str.split())

        # 确保货币符号和数字之间没有空格
        amount_str = re.sub(r'([$£€])\s+', r'\1', amount_str)
        amount_str = re.sub(r'(USD|GBP|EUR)\s+', r'\1 ', amount_str)

        return amount_str

    def get_context(self, content, search_value, info_type):
        """获取抽取值的上下文"""
        # 对于人名，可能需要搜索部分匹配
        if info_type == 'person_names':
            # 尝试搜索姓或名
            name_parts = search_value.split()
            pos = -1
            for part in name_parts:
                pos = content.lower().find(part.lower())
                if pos >= 0:
                    break
        else:
            pos = content.lower().find(search_value.lower())

        if pos >= 0:
            start = max(0, pos - 100)
            end = min(len(content), pos + len(search_value) + 100)
            context = content[start:end]
            # 替换换行符为空格
            context = context.replace('\n', ' ')
            return context
        else:
            return ""

    def extract_information(self, doc_id, content):
        """从单个文档中抽取信息"""
        extracted = {}

        for info_type, config in self.extraction_patterns.items():
            pattern = config['pattern']
            matches = re.findall(pattern, content, re.IGNORECASE)

            # 清理和去重
            if info_type == 'money_amounts':
                # 标准化金额格式
                cleaned_matches = []
                for match in matches:
                    if isinstance(match, tuple):
                        match_str = ' '.join(filter(None, match))
                    else:
                        match_str = match
                    cleaned_match = self.clean_money_amount(match_str)
                    # 过滤掉太短的匹配
                    if len(cleaned_match) > 2:
                        cleaned_matches.append(cleaned_match)
                matches = list(dict.fromkeys(cleaned_matches))  # 去重并保持顺序

            elif info_type == 'percentages':
                # 标准化百分比格式
                cleaned_matches = []
                for match in matches:
                    match = match.replace('percent', '%').strip()
                    cleaned_matches.append(match)
                matches = list(dict.fromkeys(cleaned_matches))

            elif info_type == 'person_names':
                # 过滤可能的误匹配
                filtered_matches = []
                common_titles = {'Mr', 'Mrs', 'Ms', 'Dr', 'Prof', 'President', 'CEO', 'CFO', 'CTO'}

                for match in matches:
                    words = match.split()
                    # 确保至少有两个单词（名和姓）
                    if len(words) >= 2:
                        # 检查是否全是大写（可能是缩写）
                        if not all(w.isupper() for w in words):
                            # 检查是否包含常见的非人名模式
                            if not any(word in ['The', 'This', 'That', 'These', 'Those'] for word in words):
                                # 添加可能的职称
                                for i, prev_match in enumerate(content.split()):
                                    if prev_match in common_titles and match in content[content.find(prev_match):]:
                                        match = f"{prev_match} {match}"
                                        break
                                filtered_matches.append(match)

                # 去重并限制数量
                matches = list(dict.fromkeys(filtered_matches))[:15]

            elif info_type == 'organizations':
                # 过滤掉太短的组织名
                matches = list(dict.fromkeys([m for m in matches if len(m.split()) >= 2]))

            elif info_type == 'quoted_text':
                # 只保留合理长度的引用
                matches = list(dict.fromkeys([m for m in matches if 10 < len(m) < 200]))[:5]

            elif info_type == 'dates':
                # 标准化日期格式
                matches = list(dict.fromkeys(matches))

            elif info_type == 'numbers_with_units':
                # 标准化带单位的数值
                matches = list(dict.fromkeys(matches))

            if matches:
                # 为每个匹配值添加上下文
                matches_with_context = []
                for match in matches:
                    context = self.get_context(content, match, info_type)
                    matches_with_context.append({
                        'value': match,
                        'context': context
                    })
                extracted[info_type] = matches_with_context

        return extracted

    def extract_all(self):
        """从所有文档中抽取信息"""
        print("\n正在抽取信息...")

        for doc_id, content in self.documents.items():
            extracted = self.extract_information(doc_id, content)

            # 保存抽取结果
            for info_type, matches_with_context in extracted.items():
                for match_info in matches_with_context:
                    self.extracted_info[info_type].append({
                        'doc_id': doc_id,
                        'value': match_info['value'],
                        'context': match_info['context'],
                        'title': self.metadata[doc_id]['title']
                    })

        print("信息抽取完成！")

    def display_statistics(self):
        """显示抽取统计信息"""
        print("\n========== 抽取统计 ==========")
        for info_type, config in self.extraction_patterns.items():
            count = len(self.extracted_info[info_type])
            print(f"{config['description']}: {count} 个")
        print("==============================\n")

    def save_results(self, output_file='extraction_results.json'):
        """保存抽取结果"""
        results = {}
        for info_type, items in self.extracted_info.items():
            results[info_type] = items

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"抽取结果已保存到 {output_file}")

    def search_extracted_info(self, info_type=None, keyword=None):
        """搜索抽取的信息"""
        results = []

        if info_type and info_type in self.extracted_info:
            items = self.extracted_info[info_type]
            if keyword:
                # 按关键词过滤
                items = [item for item in items if keyword.lower() in item['value'].lower()]
            results = items
        elif keyword:
            # 在所有类型中搜索
            for itype, items in self.extracted_info.items():
                for item in items:
                    if keyword.lower() in item['value'].lower():
                        results.append({
                            'type': itype,
                            'doc_id': item['doc_id'],
                            'value': item['value'],
                            'context': item['context'],
                            'title': item['title']
                        })

        return results

    def interactive_mode(self):
        """交互式查询界面"""
        print("\n========== 信息抽取系统 ==========")
        print("命令说明:")
        print("  1 - 按信息类型查看")
        print("  2 - 搜索特定内容")
        print("  3 - 查看某篇文档的所有抽取信息")
        print("  4 - 显示统计信息")
        print("  5 - 人工评价抽取结果")
        print("  quit - 退出")
        print("===================================\n")

        while True:
            command = input("请输入命令 (1-5 或 quit): ").strip()

            if command == 'quit':
                print("感谢使用！")
                break

            elif command == '1':
                print("\n可用的信息类型:")
                for i, (info_type, config) in enumerate(self.extraction_patterns.items(), 1):
                    print(f"  {i}. {config['description']} ({info_type})")

                try:
                    choice = int(input("选择类型 (输入数字): "))
                    info_types = list(self.extraction_patterns.keys())
                    if 1 <= choice <= len(info_types):
                        selected_type = info_types[choice - 1]
                        items = self.extracted_info[selected_type]

                        print(f"\n{self.extraction_patterns[selected_type]['description']}:")
                        for i, item in enumerate(items[:20], 1):  # 显示前20个
                            print(f"{i}. {item['value']}")
                            print(f"   来源: 文档{item['doc_id']} - {item['title'][:50]}...")
                            if item['context']:
                                print(f"   上下文: ...{item['context']}...")

                        if len(items) > 20:
                            print(f"\n... 还有 {len(items) - 20} 个结果")
                except:
                    print("无效输入")

            elif command == '2':
                keyword = input("输入搜索关键词: ").strip()
                if keyword:
                    results = self.search_extracted_info(keyword=keyword)
                    print(f"\n找到 {len(results)} 个结果:")
                    for i, result in enumerate(results[:20], 1):
                        if 'type' in result:
                            print(f"{i}. [{self.extraction_patterns[result['type']]['description']}] {result['value']}")
                            print(f"   来源: 文档{result['doc_id']} - {result['title'][:50]}...")
                            if result['context']:
                                print(f"   上下文: ...{result['context']}...")
                        else:
                            print(f"{i}. {result['value']}")
                            print(f"   来源: 文档{result['doc_id']} - {result['title'][:50]}...")
                            if result['context']:
                                print(f"   上下文: ...{result['context']}...")

            elif command == '3':
                try:
                    doc_id = int(input("输入文档ID (1-120): "))
                    if doc_id in self.documents:
                        print(f"\n文档 {doc_id}: {self.metadata[doc_id]['title']}")
                        print("抽取的信息:")

                        found_any = False
                        for info_type, items in self.extracted_info.items():
                            doc_items = [item for item in items if item['doc_id'] == doc_id]
                            if doc_items:
                                found_any = True
                                print(f"\n{self.extraction_patterns[info_type]['description']}:")
                                for item in doc_items:
                                    print(f"  - {item['value']}")
                                    if item['context']:
                                        print(f"    上下文: ...{item['context']}...")

                        if not found_any:
                            print("该文档没有抽取到信息")
                except:
                    print("无效的文档ID")

            elif command == '4':
                self.display_statistics()

            elif command == '5':
                self.evaluate_extraction()

            else:
                print("无效命令")

    def evaluate_extraction(self):
        """人工评价抽取结果"""
        print("\n========== 人工评价 ==========")
        print("随机选择10个抽取结果进行评价")
        print("输入 y (正确) 或 n (错误)")
        print("==============================\n")

        import random

        # 随机选择评价样本
        all_samples = []
        for info_type, items in self.extracted_info.items():
            sample_items = items[:5] if len(items) > 5 else items
            for item in sample_items:
                all_samples.append({
                    'type': info_type,
                    'value': item['value'],
                    'doc_id': item['doc_id'],
                    'title': item['title']
                })

        if len(all_samples) > 10:
            samples = random.sample(all_samples, 10)
        else:
            samples = all_samples

        correct = 0
        total = len(samples)

        for i, sample in enumerate(samples, 1):
            print(f"\n样本 {i}/{total}")
            print(f"类型: {self.extraction_patterns[sample['type']]['description']}")
            print(f"抽取值: {sample['value']}")
            print(f"来源文档{sample['doc_id']}: {sample['title'][:80]}...")

            # 显示上下文
            doc_content = self.documents[sample['doc_id']]
            # 查找值在文档中的位置
            search_value = sample['value']
            # 对于人名，可能需要搜索部分匹配
            if sample['type'] == 'person_names':
                # 尝试搜索姓或名
                name_parts = search_value.split()
                pos = -1
                for part in name_parts:
                    pos = doc_content.lower().find(part.lower())
                    if pos >= 0:
                        break
            else:
                pos = doc_content.lower().find(search_value.lower())

            if pos >= 0:
                start = max(0, pos - 100)
                end = min(len(doc_content), pos + len(search_value) + 100)
                context = doc_content[start:end]
                # 高亮显示匹配的部分
                context = context.replace('\n', ' ')
                print(f"上下文: ...{context}...")

            evaluation = input("是否正确？(y/n): ").strip().lower()
            if evaluation == 'y':
                correct += 1

        accuracy = correct / total * 100 if total > 0 else 0
        print(f"\n评价完成！")
        print(f"准确率: {accuracy:.1f}% ({correct}/{total})")

        # 保存评价结果
        with open('evaluation_results.txt', 'a', encoding='utf-8') as f:
            f.write(f"\n评价时间: {datetime.now()}\n")
            f.write(f"样本数: {total}\n")
            f.write(f"正确数: {correct}\n")
            f.write(f"准确率: {accuracy:.1f}%\n")
            f.write("-" * 40 + "\n")


def main():
    # 创建信息抽取系统
    ie_system = InformationExtractionSystem()

    # 加载文档
    ie_system.load_documents()

    # 执行信息抽取
    ie_system.extract_all()

    # 显示统计信息
    ie_system.display_statistics()

    # 保存结果
    ie_system.save_results()

    # 启动交互模式
    ie_system.interactive_mode()


if __name__ == '__main__':
    main()