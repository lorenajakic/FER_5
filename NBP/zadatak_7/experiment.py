import psycopg2
import numpy as np
import time

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
            'hnsw_384_l2': {'enn_time_ms': None, 'ann_time_ms': None},
            'hnsw_384_ip': {'enn_time_ms': None, 'ann_time_ms': None},
            'hnsw_384_cosine': {'enn_time_ms': None, 'ann_time_ms': None},
            'hnsw_768_l2': {'enn_time_ms': None, 'ann_time_ms': None},
            'hnsw_768_ip': {'enn_time_ms': None, 'ann_time_ms': None},
            'hnsw_768_cosine': {'enn_time_ms': None, 'ann_time_ms': None},
            'ivfflat_384_l2': {'enn_time_ms': None, 'ann_time_ms': None},
            'ivfflat_384_ip': {'enn_time_ms': None, 'ann_time_ms': None},
            'ivfflat_384_cosine': {'enn_time_ms': None, 'ann_time_ms': None},
            'ivfflat_768_l2': {'enn_time_ms': None, 'ann_time_ms': None},
            'ivfflat_768_ip': {'enn_time_ms': None, 'ann_time_ms': None},
            'ivfflat_768_cosine': {'enn_time_ms': None, 'ann_time_ms': None}
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
            
            t0 = time.perf_counter()
            cur.execute(sql, (query_id, query_vector, k))
            enn_time_ms = (time.perf_counter() - t0) * 1000.0
            
            # ANN
            cur.execute("SET enable_seqscan = off")

            sql = f"""
                    SELECT id FROM {table_name} 
                    WHERE id != %s 
                    ORDER BY {vector_col} {set_operator(metric)} %s 
                    LIMIT %s
                """
            
            t1 = time.perf_counter()
            cur.execute(sql, (query_id, query_vector, k))
            ann_time_ms = (time.perf_counter() - t1) * 1000.0
            
            experiment_results[f"{table_type}_{dim}_{metric}"]['enn_time_ms'] = enn_time_ms
            experiment_results[f"{table_type}_{dim}_{metric}"]['ann_time_ms'] = ann_time_ms
        
        results.append(experiment_results)
    
    cur.close()
    conn.close()
    
    return results

def calculate_recall(results):
    avg_times = {}
    combinations = [
        'hnsw_384_l2', 'hnsw_384_ip', 'hnsw_384_cosine',
        'hnsw_768_l2', 'hnsw_768_ip', 'hnsw_768_cosine',
        'ivfflat_384_l2', 'ivfflat_384_ip', 'ivfflat_384_cosine',
        'ivfflat_768_l2', 'ivfflat_768_ip', 'ivfflat_768_cosine'
    ]
    for combination in combinations:
        enn_times = []
        ann_times = []
        for experiment in results:
            enn_times.append(experiment[combination]['enn_time_ms'])
            ann_times.append(experiment[combination]['ann_time_ms'])
        enn_avg = float(np.mean(enn_times))
        ann_avg = float(np.mean(ann_times))
        avg_times[combination] = {
            'enn_avg_ms': enn_avg,
            'ann_avg_ms': ann_avg
        }
    return avg_times

def print_table(avg_times):
    print("ind_type\tembedding\t\tmeasure\t\tENN_avg(ms)\t\tANN_avg(ms)")
    print("-" * 100)
        
    print(f"HNSW\t\tembedding384\t\tL2\t\t{avg_times['hnsw_384_l2']['enn_avg_ms']:.4f}\t\t\t{avg_times['hnsw_384_l2']['ann_avg_ms']:.4f}")
    print(f"HNSW\t\tembedding384\t\tcosine\t\t{avg_times['hnsw_384_cosine']['enn_avg_ms']:.4f}\t\t\t{avg_times['hnsw_384_cosine']['ann_avg_ms']:.4f}")
    print(f"HNSW\t\tembedding384\t\tinner_product\t{avg_times['hnsw_384_ip']['enn_avg_ms']:.4f}\t\t\t{avg_times['hnsw_384_ip']['ann_avg_ms']:.4f}")
    print(f"HNSW\t\tembedding768\t\tL2\t\t{avg_times['hnsw_768_l2']['enn_avg_ms']:.4f}\t\t\t{avg_times['hnsw_768_l2']['ann_avg_ms']:.4f}")
    print(f"HNSW\t\tembedding768\t\tcosine\t\t{avg_times['hnsw_768_cosine']['enn_avg_ms']:.4f}\t\t\t{avg_times['hnsw_768_cosine']['ann_avg_ms']:.4f}")
    print(f"HNSW\t\tembedding768\t\tinner_product\t{avg_times['hnsw_768_ip']['enn_avg_ms']:.4f}\t\t\t{avg_times['hnsw_768_ip']['ann_avg_ms']:.4f}")
        
    print(f"IVFFlat\t\tembedding384\t\tL2\t\t{avg_times['ivfflat_384_l2']['enn_avg_ms']:.4f}\t\t\t{avg_times['ivfflat_384_l2']['ann_avg_ms']:.4f}")
    print(f"IVFFlat\t\tembedding384\t\tcosine\t\t{avg_times['ivfflat_384_cosine']['enn_avg_ms']:.4f}\t\t\t{avg_times['ivfflat_384_cosine']['ann_avg_ms']:.4f}")
    print(f"IVFFlat\t\tembedding384\t\tinner_product\t{avg_times['ivfflat_384_ip']['enn_avg_ms']:.4f}\t\t\t{avg_times['ivfflat_384_ip']['ann_avg_ms']:.4f}")
    print(f"IVFFlat\t\tembedding768\t\tL2\t\t{avg_times['ivfflat_768_l2']['enn_avg_ms']:.4f}\t\t\t{avg_times['ivfflat_768_l2']['ann_avg_ms']:.4f}")
    print(f"IVFFlat\t\tembedding768\t\tcosine\t\t{avg_times['ivfflat_768_cosine']['enn_avg_ms']:.4f}\t\t\t{avg_times['ivfflat_768_cosine']['ann_avg_ms']:.4f}")
    print(f"IVFFlat\t\tembedding768\t\tinner_product\t{avg_times['ivfflat_768_ip']['enn_avg_ms']:.4f}\t\t\t{avg_times['ivfflat_768_ip']['ann_avg_ms']:.4f}")

if __name__ == "__main__":
    results = experiment()
    avg_times = calculate_recall(results)
    print_table(avg_times)