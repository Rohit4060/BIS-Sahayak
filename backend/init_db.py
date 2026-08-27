from dotenv import load_dotenv
load_dotenv()

from database import Base, engine
import models  # noqa: F401  (import so the models register with Base before create_all)

if __name__ == "__main__":
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Done. Tables created: documents, document_chunks")