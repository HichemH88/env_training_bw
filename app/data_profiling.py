# data_profiling.py
import duckdb
import pandas as pd
import numpy as np
from datetime import datetime
import os

def data_profiling():
    """Comprehensive data profiling for all tables in DuckDB"""
    
    db_file = '/app/my_data.duckdb'
    
    if not os.path.exists(db_file):
        print(f"❌ Database file not found: {db_file}")
        return
    
    print(f"✅ Database file found: {db_file}")
    print("🚀 Starting comprehensive data profiling...")
    print("=" * 80)
    
    con = duckdb.connect(db_file)
    tables = con.execute("SHOW TABLES").fetchall()
    
    if not tables:
        print("❌ No tables found in the database")
        con.close()
        return
    
    os.makedirs('data_profiles', exist_ok=True)
    
    all_profiles = {}
    
    for table in tables:
        table_name = table[0]
        print(f"\n📊 PROFILING TABLE: {table_name}")
        print("-" * 60)
        
        try:
            profile = profile_table(con, table_name)
            all_profiles[table_name] = profile
            save_table_profile(profile, table_name)
            
        except Exception as e:
            print(f"❌ Error profiling table {table_name}: {e}")
            all_profiles[table_name] = {'error': str(e)}
    
    save_comprehensive_report(all_profiles)
    con.close()
    print(f"\n✅ Data profiling completed! Reports saved in 'data_profiles' directory")

def profile_table(con, table_name):
    """Profile a single table"""
    
    profile = {
        'table_name': table_name,
        'timestamp': datetime.now(),
        'basic_stats': {},
        'column_profiles': {},
        'data_quality_issues': [],
        'recommendations': []
    }
    
    row_count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    profile['basic_stats']['row_count'] = row_count
    
    if row_count == 0:
        profile['data_quality_issues'].append("Table is empty")
        return profile
    
    schema = con.execute(f"PRAGMA table_info({table_name})").fetchall()
    profile['basic_stats']['column_count'] = len(schema)
    
    for col in schema:
        col_id, col_name, col_type, not_null, default_val, pk = col
        profile['column_profiles'][col_name] = profile_column(con, table_name, col_name, col_type, not_null, row_count)
    
    perform_data_quality_checks(con, table_name, profile)
    return profile

def profile_column(con, table_name, col_name, col_type, not_null, row_count):
    """Profile a single column"""
    
    column_profile = {
        'data_type': col_type,
        'is_required': not_null == 1,
        'stats': {}
    }
    
    try:
        null_count = con.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {col_name} IS NULL").fetchone()[0]
        distinct_count = con.execute(f"SELECT COUNT(DISTINCT {col_name}) FROM {table_name}").fetchone()[0]
        
        column_profile['stats']['null_count'] = null_count
        column_profile['stats']['distinct_count'] = distinct_count
        column_profile['stats']['total_count'] = row_count
        column_profile['stats']['null_percentage'] = (null_count / row_count) * 100 if row_count else 0
        
        # Numeric columns
        if any(num_type in col_type.upper() for num_type in ['INT', 'FLOAT', 'DOUBLE', 'DECIMAL', 'NUMERIC']):
            stats = con.execute(f"""
                SELECT 
                    MIN({col_name}), MAX({col_name}), AVG({col_name}), 
                    STDDEV({col_name}), COUNT({col_name})
                FROM {table_name}
            """).fetchone()
            
            column_profile['stats'].update({
                'min': stats[0],
                'max': stats[1],
                'mean': stats[2],
                'std_dev': stats[3],
                'non_null_count': stats[4]
            })
        
        # Date/time
        elif 'DATE' in col_type.upper() or 'TIME' in col_type.upper():
            min_max = con.execute(f"""
                SELECT MIN({col_name}), MAX({col_name}) 
                FROM {table_name} WHERE {col_name} IS NOT NULL
            """).fetchone()
            if min_max and min_max[0]:
                column_profile['stats'].update({
                    'min_date': min_max[0],
                    'max_date': min_max[1]
                })
        
        # Boolean
        elif 'BOOL' in col_type.upper():
            value_counts = con.execute(f"""
                SELECT {col_name}, COUNT(*) 
                FROM {table_name} GROUP BY {col_name} ORDER BY COUNT(*) DESC
            """).fetchall()
            column_profile['stats']['value_distribution'] = dict(value_counts)
        
        # String/text
        else:
            length_stats = con.execute(f"""
                SELECT MIN(LENGTH({col_name})), MAX(LENGTH({col_name})), AVG(LENGTH({col_name}))
                FROM {table_name} WHERE {col_name} IS NOT NULL
            """).fetchone()
            
            top_values = con.execute(f"""
                SELECT {col_name}, COUNT(*) 
                FROM {table_name} WHERE {col_name} IS NOT NULL
                GROUP BY {col_name} ORDER BY COUNT(*) DESC LIMIT 10
            """).fetchall()
            
            column_profile['stats'].update({
                'min_length': length_stats[0],
                'max_length': length_stats[1],
                'avg_length': length_stats[2],
                'top_values': [(str(v), c) for v, c in top_values]
            })
            
    except Exception as e:
        column_profile['error'] = f"Error profiling column: {str(e)}"
    
    return column_profile

def perform_data_quality_checks(con, table_name, profile):
    """Perform data quality checks"""
    
    # Duplicate rows
    duplicate_check = con.execute(f"""
        SELECT COUNT(*) - (SELECT COUNT(*) FROM (SELECT DISTINCT * FROM {table_name}))
    """).fetchone()[0]
    
    if duplicate_check > 0:
        profile['data_quality_issues'].append(f"{duplicate_check} duplicate rows found")
        profile['recommendations'].append("Consider removing duplicate rows")
    
    # PK checks
    schema = con.execute(f"PRAGMA table_info({table_name})").fetchall()
    pk_columns = [col[1] for col in schema if col[5] > 0]
    
    for pk_col in pk_columns:
        null_pk = con.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {pk_col} IS NULL").fetchone()[0]
        if null_pk > 0:
            profile['data_quality_issues'].append(f"Primary key column '{pk_col}' contains {null_pk} NULL values")
        
        duplicate_pk = con.execute(f"""
            SELECT {pk_col}, COUNT(*) FROM {table_name} 
            GROUP BY {pk_col} HAVING COUNT(*) > 1
        """).fetchall()
        
        if duplicate_pk:
            profile['data_quality_issues'].append(f"Primary key column '{pk_col}' has {len(duplicate_pk)} duplicate values")
    
    # Column quality
    for col_name, col_profile in profile['column_profiles'].items():
        col_type = col_profile['data_type']
        null_pct = col_profile['stats'].get('null_percentage', 0)
        
        if null_pct > 50:
            profile['data_quality_issues'].append(f"Column '{col_name}' has high null percentage: {null_pct:.1f}%")
        
        if any(num_type in col_type.upper() for num_type in ['INT', 'FLOAT', 'DOUBLE']):
            min_val = col_profile['stats'].get('min')
            max_val = col_profile['stats'].get('max')
            if min_val is not None and max_val is not None:
                if min_val < 0 and 'ID' in col_name.upper():
                    profile['data_quality_issues'].append(f"ID column '{col_name}' contains negative values")
                if max_val > 1e9 and 'AMOUNT' in col_name.upper():
                    profile['data_quality_issues'].append(f"Amount column '{col_name}' contains very large values")

def save_table_profile(profile, table_name):
    """Save individual table profile to file"""
    
    filename = f"data_profiles/{table_name}_profile.txt"
    
    with open(filename, 'w', encoding="utf-8") as f:
        f.write(f"DATA PROFILE REPORT - {table_name}\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {profile['timestamp']}\n")
        f.write(f"Total rows: {profile['basic_stats']['row_count']:,}\n")
        f.write(f"Total columns: {profile['basic_stats']['column_count']}\n\n")
        
        f.write("COLUMN PROFILES:\n")
        f.write("-" * 40 + "\n")
        
        for col_name, col_profile in profile['column_profiles'].items():
            f.write(f"\n📊 {col_name} ({col_profile['data_type']})")
            f.write(f"\n   Required: {col_profile['is_required']}")
            
            if 'error' in col_profile:
                f.write(f"\n   Error: {col_profile['error']}\n")
                continue
            
            stats = col_profile['stats']
            f.write(f"\n   Null values: {stats.get('null_count', 0):,} ({stats.get('null_percentage', 0):.1f}%)")
            f.write(f"\n   Distinct values: {stats.get('distinct_count', 0):,}")
            
            if 'min' in stats:
                f.write(f"\n   Range: {stats['min']} to {stats['max']}")
                f.write(f"\n   Mean: {stats.get('mean', 0):.2f}, Std Dev: {stats.get('std_dev', 0):.2f}")
            
            if 'min_length' in stats:
                f.write(f"\n   Length: {stats['min_length']} to {stats['max_length']} chars")
                f.write(f"\n   Avg length: {stats.get('avg_length', 0):.1f} chars")
            
            if 'top_values' in stats and stats['top_values']:
                f.write(f"\n   Top values:")
                for value, count in stats['top_values'][:3]:
                    f.write(f"\n     {value}: {count:,}")
        
        if profile['data_quality_issues']:
            f.write(f"\n\n❌ DATA QUALITY ISSUES:\n")
            f.write("-" * 40 + "\n")
            for issue in profile['data_quality_issues']:
                f.write(f"• {issue}\n")
        
        if profile['recommendations']:
            f.write(f"\n💡 RECOMMENDATIONS:\n")
            f.write("-" * 40 + "\n")
            for rec in profile['recommendations']:
                f.write(f"• {rec}\n")
    
    print(f"   ✓ Profile saved: {filename}")

def save_comprehensive_report(all_profiles):
    """Save comprehensive report across all tables"""
    
    filename = "data_profiles/comprehensive_data_quality_report.txt"
    
    with open(filename, 'w', encoding="utf-8") as f:
        f.write("COMPREHENSIVE DATA QUALITY REPORT\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {datetime.now()}\n")
        f.write(f"Total tables analyzed: {len(all_profiles)}\n\n")
        
        total_rows = sum(prof['basic_stats']['row_count'] for prof in all_profiles.values() if 'basic_stats' in prof)
        total_columns = sum(prof['basic_stats']['column_count'] for prof in all_profiles.values() if 'basic_stats' in prof)
        
        f.write(f"📈 SUMMARY STATISTICS:\n")
        f.write(f"Total rows across all tables: {total_rows:,}\n")
        f.write(f"Total columns across all tables: {total_columns}\n\n")
        
        f.write("📊 TABLE OVERVIEW:\n")
        f.write("-" * 40 + "\n")
        for table_name, profile in all_profiles.items():
            if 'basic_stats' in profile:
                f.write(f"{table_name}: {profile['basic_stats']['row_count']:,} rows, {profile['basic_stats']['column_count']} columns\n")
        
        all_issues = []
        for profile in all_profiles.values():
            if 'data_quality_issues' in profile:
                all_issues.extend(profile['data_quality_issues'])
        
        if all_issues:
            f.write(f"\n❌ TOTAL DATA QUALITY ISSUES FOUND: {len(all_issues)}\n")
            f.write("-" * 50 + "\n")
            for i, issue in enumerate(all_issues, 1):
                f.write(f"{i}. {issue}\n")
        else:
            f.write(f"\n✅ No data quality issues found!\n")
    
    print(f"   ✓ Comprehensive report saved: {filename}")

if __name__ == "__main__":
    data_profiling()
