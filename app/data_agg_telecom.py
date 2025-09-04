import psycopg2
from psycopg2 import sql

def create_aggregated_view():
    """Creates an aggregated view in PostgreSQL database"""
    try:
        # Database connection parameters
        conn = psycopg2.connect(
            host="db-demo",
            database="mydb",
            user="admin",
            password="admin"
        )
        cursor = conn.cursor()
        
        print("Creating aggregated view...")
        
        # SQL to create the view
        create_view_sql = """
        CREATE OR REPLACE VIEW dev.agg_usage AS
        SELECT 
            sum("Total.Day.Minutes") as minutes,
            sum("Total.Day.Calls") as call_1, 
            sum("Total.Day.Charge") as day_charge,
            sum("Total.Eve.Minutes") as minu_eve,
            sum("Total.Eve.Calls") as call_eve, 
            sum("Total.Eve.Charge") as eve_charge,
            sum("Total.Night.Minutes") as night_minutes,
            sum("Total.Night.Calls") as night_calls, 
            sum("Total.Night.Charge") as night_charge,
            sum("Total.Intl.Minutes") as intl_minutes,
            sum("Total.Intl.Calls") as calls_int,
            sum("Total.Intl.Charge") as charge_init
        FROM dev.call_details;
        """
        
        cursor.execute(create_view_sql)
        conn.commit()
        
        print("Successfully created dev.agg_usage view")
        
        # Verify the view exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.views 
            WHERE table_schema = 'dev' 
            AND table_name = 'agg_usage'
        """)
        count = cursor.fetchone()[0]
        
        if count == 1:
            print("View verification successful")
        else:
            print("View creation verification failed")
            
    except Exception as e:
        print(f"Error creating view: {str(e)}")
        conn.rollback()
    finally:
        if conn:
            cursor.close()
            conn.close()
            print("Database connection closed")

if __name__ == "__main__":
    create_aggregated_view()