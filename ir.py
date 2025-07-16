import os
import csv
import math
import re
from collections import defaultdict
import json
import pickle


class InformationRetrievalSystem:
    def __init__(self, articles_dir='articles', metadata_file='metadata.csv'):
        self.articles_dir = articles_dir
        self.metadata_file = metadata_file
        self.documents = {}  # {doc_id: content}
        self.metadata = {}  # {doc_id: metadata}
        self.inverted_index = defaultdict(list)  # {term: [(doc_id, tf), ...]}
        self.doc_vectors = {}  # {doc_id: {term: tf-idf}}
        self.doc_lengths = {}  # {doc_id: vector_length}
        self.idf_values = {}  # {term: idf}
        self.N = 0  # 文档总数

    def load_documents(self):
        """加载所有文档和元数据"""
        print("正在加载文档...")

        # 加载元数据
        import chardet
        # 检测编码
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
        for doc_id, meta in self.metadata.items():
            filepath = os.path.join(self.articles_dir, meta['filename'])
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                self.documents[doc_id] = content

        self.N = len(self.documents)
        print(f"已加载 {self.N} 篇文档")

    def preprocess_text(self, text):
        """预处理文本：转小写，分词，去除停用词"""
        # 转小写
        text = text.lower()

        # 提取单词（只保留字母）
        words = re.findall(r'[a-z]+', text)

        # 简单的停用词列表
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                     'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'been', 'be',
                     'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
                     'could', 'may', 'might', 'must', 'shall', 'can', 'this', 'that', 'these',
                     'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'them', 'their',
                     'what', 'which', 'who', 'when', 'where', 'why', 'how', 'all', 'each',
                     'every', 'some', 'any', 'many', 'much', 'most', 'other', 'another',
                     'such', 'no', 'not', 'only', 'own', 'same', 'so', 'than', 'too',
                     'very', 's', 't', 'just', 'now', 'here', 'there', 'also', 'as'}

        # 过滤停用词和短词
        words = [w for w in words if w not in stopwords and len(w) > 2]

        return words

    def build_inverted_index(self):
        """构建倒排索引"""
        print("正在构建倒排索引...")

        # 计算每个文档中每个词的词频
        for doc_id, content in self.documents.items():
            words = self.preprocess_text(content)
            word_count = defaultdict(int)

            # 统计词频
            for word in words:
                word_count[word] += 1

            # 添加到倒排索引
            for word, count in word_count.items():
                tf = count / len(words) if words else 0  # 归一化的词频
                self.inverted_index[word].append((doc_id, tf))
        # 计算IDF值
        for term, postings in self.inverted_index.items():
            df = len(postings)  # 文档频率
            self.idf_values[term] = math.log(self.N / df)

        print(f"倒排索引构建完成，共 {len(self.inverted_index)} 个词条")

    def compute_document_vectors(self):
        """计算文档的TF-IDF向量"""
        print("正在计算文档向量...")

        for doc_id in self.documents:
            self.doc_vectors[doc_id] = {}

            # 获取文档中的所有词及其TF-IDF值
            for term, postings in self.inverted_index.items():
                for posting_doc_id, tf in postings:
                    if posting_doc_id == doc_id:
                        tf_idf = tf * self.idf_values[term]
                        self.doc_vectors[doc_id][term] = tf_idf

            # 计算文档向量长度（用于余弦相似度归一化）
            length = math.sqrt(sum(val ** 2 for val in self.doc_vectors[doc_id].values()))
            self.doc_lengths[doc_id] = length

        print("文档向量计算完成")

    def save_index(self, index_file='index.pkl'):
        """保存索引到文件"""
        print(f"正在保存索引到 {index_file}...")
        with open(index_file, 'wb') as f:
            pickle.dump({
                'inverted_index': dict(self.inverted_index),
                'idf_values': self.idf_values,
                'doc_vectors': self.doc_vectors,
                'doc_lengths': self.doc_lengths,
                'N': self.N
            }, f)
        print("索引保存完成")

    def load_index(self, index_file='index.pkl'):
        """从文件加载索引"""
        print(f"正在从 {index_file} 加载索引...")
        with open(index_file, 'rb') as f:
            data = pickle.load(f)
            self.inverted_index = defaultdict(list, data['inverted_index'])
            self.idf_values = data['idf_values']
            self.doc_vectors = data['doc_vectors']
            self.doc_lengths = data['doc_lengths']
            self.N = data['N']
        print("索引加载完成")

    def search(self, query, top_k=10):
        """使用向量空间模型进行搜索"""
        # 预处理查询
        query_terms = self.preprocess_text(query)
        if not query_terms:
            return []

        # 构建查询向量
        query_vector = {}
        query_term_count = defaultdict(int)
        for term in query_terms:
            query_term_count[term] += 1

        for term, count in query_term_count.items():
            if term in self.idf_values:
                tf = count / len(query_terms)
                query_vector[term] = tf * self.idf_values[term]

        if not query_vector:
            return []

        # 计算查询向量长度
        query_length = math.sqrt(sum(val ** 2 for val in query_vector.values()))

        # 计算与每个文档的余弦相似度
        scores = {}
        for doc_id in self.documents:
            score = 0
            for term, query_weight in query_vector.items():
                if term in self.doc_vectors[doc_id]:
                    score += query_weight * self.doc_vectors[doc_id][term]

            # 余弦相似度归一化
            if self.doc_lengths[doc_id] > 0 and query_length > 0:
                score = score / (self.doc_lengths[doc_id] * query_length)

            if score > 0:
                scores[doc_id] = score

        # 按相关度排序并返回前k个结果
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        results = []
        for doc_id, score in sorted_results:
            # 找出匹配的内容片段
            content = self.documents[doc_id]
            sentences = re.split(r'[.!?]', content)
            matching_sentences = []

            for sentence in sentences:
                sentence_lower = sentence.lower()
                for term in query_terms:
                    if term in sentence_lower:
                        matching_sentences.append(sentence.strip())
                        break

            # 获取前3个匹配的句子作为摘要
            summary = '. '.join(matching_sentences[:3]) + '.' if matching_sentences else ''

            results.append({
                'doc_id': doc_id,
                'score': score,
                'title': self.metadata[doc_id]['title'],
                'summary': summary,
                'url': self.metadata[doc_id]['url'],
                'date': self.metadata[doc_id]['date']
            })

        return results

    def build_index(self):
        """构建完整的索引系统"""
        self.load_documents()
        self.build_inverted_index()
        self.compute_document_vectors()
        self.save_index()

    def interactive_search(self):
        """交互式搜索界面"""
        print("\n========== 信息检索系统 ==========")
        print("输入查询词进行搜索，输入 'quit' 退出")
        print("==================================\n")

        while True:
            query = input("请输入查询词: ").strip()

            if query.lower() == 'quit':
                print("感谢使用！")
                break

            if not query:
                continue

            print(f"\n正在搜索: '{query}'...")
            results = self.search(query)

            if not results:
                print("没有找到相关文档。\n")
            else:
                print(f"\n找到 {len(results)} 个相关文档:\n")
                for i, result in enumerate(results, 1):
                    print(f"{i}. 相关度: {result['score']:.4f}")
                    print(f"   标题: {result['title']}")
                    print(f"   日期: {result['date']}")
                    print(f"   URL: {result['url']}")
                    if result['summary']:
                        print(f"   匹配内容: {result['summary'][:200]}...")
                    print()


def main():
    # 创建信息检索系统
    ir_system = InformationRetrievalSystem()

    # 检查是否已有索引文件
    if os.path.exists('index.pkl'):
        print("发现已有索引文件，是否重新构建？(y/n): ", end='')
        choice = input().strip().lower()
        if choice == 'y':
            ir_system.build_index()
        else:
            ir_system.load_index()
            ir_system.load_documents()
    else:
        ir_system.build_index()

    # 启动交互式搜索
    ir_system.interactive_search()


if __name__ == '__main__':
    main()