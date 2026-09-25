import psycopg2
import numpy as np

DB_CONFIG = {
    "dbname": "ankanePgVector",
    "user": "postgres", 
    "password": "bazepodataka",
    "host": "localhost",
    "port": "55432"
}

def set_operator(metric):
    if metric == 'l2':
        return '<->'
    elif metric == 'ip':
        return '<#>'
    elif metric == 'cosine':
        return '<=>'

def experiment():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SET hnsw.ef_search = 500")
    cur.execute("SET ivfflat.probes = 100")  
    
    results = []
    k = 500
    
    for experiment in range(20):      
        cur.execute("""
            SELECT id, vector_384, vector_768 
            FROM articles_vectors 
            ORDER BY RANDOM() 
            LIMIT 1
        """)
        query_id, query_384, query_768 = cur.fetchone()
        
        experiment_results = {
            'experiment': experiment + 1,
            'query_id': query_id,
            'hnsw_384_l2': {'enn': [], 'ann': []},
            'hnsw_384_ip': {'enn': [], 'ann': []},
            'hnsw_384_cosine': {'enn': [], 'ann': []},
            'hnsw_768_l2': {'enn': [], 'ann': []},
            'hnsw_768_ip': {'enn': [], 'ann': []},
            'hnsw_768_cosine': {'enn': [], 'ann': []},
            'ivfflat_384_l2': {'enn': [], 'ann': []},
            'ivfflat_384_ip': {'enn': [], 'ann': []},
            'ivfflat_384_cosine': {'enn': [], 'ann': []},
            'ivfflat_768_l2': {'enn': [], 'ann': []},
            'ivfflat_768_ip': {'enn': [], 'ann': []},
            'ivfflat_768_cosine': {'enn': [], 'ann': []}
        }
                
        combinations = [
            ('hnsw', '384', 'l2', query_384),
            ('hnsw', '384', 'ip', query_384),
            ('hnsw', '384', 'cosine', query_384),
            ('hnsw', '768', 'l2', query_768),
            ('hnsw', '768', 'ip', query_768),
            ('hnsw', '768', 'cosine', query_768),
            ('ivfflat', '384', 'l2', query_384),
            ('ivfflat', '384', 'ip', query_384),
            ('ivfflat', '384', 'cosine', query_384),
            ('ivfflat', '768', 'l2', query_768),
            ('ivfflat', '768', 'ip', query_768),
            ('ivfflat', '768', 'cosine', query_768)
        ]
        
        for table_type, dim, metric, query_vector in combinations:
            table_name = f"tablica_{table_type}"
            vector_col = f"vector_{dim}"
            
            # ENN
            cur.execute("SET enable_seqscan = on")

            sql = f"""
                    SELECT id FROM articles_vectors 
                    WHERE id != %s
                    ORDER BY {vector_col} {set_operator(metric)} %s 
                    LIMIT %s
                """
            
            cur.execute(sql, (query_id, query_vector, k))
            enn_results = [row[0] for row in cur.fetchall()]
            
            # ANN
            cur.execute("SET enable_seqscan = off")

            sql = f"""
                    SELECT id FROM {table_name} 
                    WHERE id != %s 
                    ORDER BY {vector_col} {set_operator(metric)} %s 
                    LIMIT %s
                """
            
            cur.execute(sql, (query_id, query_vector, k))
            ann_results = [row[0] for row in cur.fetchall()]
            
            experiment_results[f"{table_type}_{dim}_{metric}"]['enn'] = enn_results
            experiment_results[f"{table_type}_{dim}_{metric}"]['ann'] = ann_results
        
        results.append(experiment_results)
    
    cur.close()
    conn.close()
    
    return results

def calculate_recall(results):
    recall_results = {}
    
    combinations = [
        'hnsw_384_l2', 'hnsw_384_ip', 'hnsw_384_cosine',
        'hnsw_768_l2', 'hnsw_768_ip', 'hnsw_768_cosine',
        'ivfflat_384_l2', 'ivfflat_384_ip', 'ivfflat_384_cosine',
        'ivfflat_768_l2', 'ivfflat_768_ip', 'ivfflat_768_cosine'
    ]
    
    for combination in combinations:
        recalls = []
        
        for experiment in results:
            enn_set = set(experiment[combination]['enn'])
            ann_set = set(experiment[combination]['ann'])
            
            intersection = len(enn_set & ann_set)
            recall = intersection / 500
            recalls.append(recall)
        
        recall_results[combination] = np.mean(recalls)
    
    return recall_results

def print_table(recall_results):
    print("ind_type\tembedding\t\tmeasure\t\tAVG(recall)")
    print("-" * 60)
    
    print(f"HNSW\t\tembedding384\t\tL2\t\t{recall_results['hnsw_384_l2']:.4f}")
    print(f"HNSW\t\tembedding384\t\tcosine\t\t{recall_results['hnsw_384_cosine']:.4f}")
    print(f"HNSW\t\tembedding384\t\tinner_product\t{recall_results['hnsw_384_ip']:.4f}")
    print(f"HNSW\t\tembedding768\t\tL2\t\t{recall_results['hnsw_768_l2']:.4f}")
    print(f"HNSW\t\tembedding768\t\tcosine\t\t{recall_results['hnsw_768_cosine']:.4f}")
    print(f"HNSW\t\tembedding768\t\tinner_product\t{recall_results['hnsw_768_ip']:.4f}")
    
    print(f"IVFFlat\t\tembedding384\t\tL2\t\t{recall_results['ivfflat_384_l2']:.4f}")
    print(f"IVFFlat\t\tembedding384\t\tcosine\t\t{recall_results['ivfflat_384_cosine']:.4f}")
    print(f"IVFFlat\t\tembedding384\t\tinner_product\t{recall_results['ivfflat_384_ip']:.4f}")
    print(f"IVFFlat\t\tembedding768\t\tL2\t\t{recall_results['ivfflat_768_l2']:.4f}")
    print(f"IVFFlat\t\tembedding768\t\tcosine\t\t{recall_results['ivfflat_768_cosine']:.4f}")
    print(f"IVFFlat\t\tembedding768\t\tinner_product\t{recall_results['ivfflat_768_ip']:.4f}")

if __name__ == "__main__":
    results = experiment()
    recall_results = calculate_recall(results)
    print_table(recall_results)