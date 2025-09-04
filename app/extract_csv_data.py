# check_duckdb_file.py
import duckdb
import os

def check_existing_database():
    """Check if we have an existing DuckDB database file"""
    
    db_file = '/app/my_data.duckdb'
    
    if os.path.exists(db_file):
        print(f"✅ Database file found: {db_file}")
        
        # Connect to the existing database
        con = duckdb.connect(db_file)
        
        # List tables
        tables = con.execute("SHOW TABLES").fetchall()
        
        if tables:
            print("📊 Tables in database:")
            for table in tables:
                table_name = table[0]
                count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                print(f"  - {table_name}: {count} rows")
                
                # Show 5 sample rows
                print(f"    Sample data from {table_name}:")
                sample_data = con.execute(f"SELECT * FROM {table_name} LIMIT 5").fetchall()
                for i, row in enumerate(sample_data, 1):
                    print(f"      Row {i}: {row}")
                print()  # Empty line for readability
                
                
        else:
            print("❌ No tables found in the database file")
        
        con.close()
    else:
        print(f"❌ Database file not found: {db_file}")
        print("Run the loading script first to create the database")

if __name__ == "__main__":
    check_existing_database()