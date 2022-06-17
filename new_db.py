from os import environ
from dotenv import load_dotenv
load_dotenv()


detect = "SELECT COUNT(DISTINCT table_name) FROM information_schema.columns WHERE table_schema = current_database()"
create_vl = """
--
-- Database: voice_levels
--

-- --------------------------------------------------------

--
-- Table structure for table levels
--

CREATE TABLE levels (
  right_two char(2) NOT NULL,
  json_contents json NOT NULL DEFAULT '{{}}',
  PRIMARY KEY (right_two)
);

--
-- Dumping data for table levels
--

INSERT INTO levels (right_two, json_contents) VALUES
{};

CREATE TABLE prefixes (
  id char(19) NOT NULL,
  prefix char(32) NOT NULL,
  PRIMARY KEY (id)
);

INSERT INTO prefixes (id, prefix) VALUES (0, '%s');

CREATE TABLE sudo (
  id char(19) NOT NULL,
  PRIMARY KEY (id)
);

COMMIT;
""".format(f"\n".join(f"('{i:02d}', '{{}}')," for i in range(100)).rstrip(","))

# Create token now unused
create_token = """
--
-- Database: voice_levels
--

--
-- Table structure for table token
--

CREATE TABLE token (
  onerow bool PRIMARY KEY DEFAULT TRUE,
  token text NOT NULL,
  CONSTRAINT onerow CHECK (onerow)
);

--
-- Dumping data for table token
--

INSERT INTO token (token) VALUES
('%s');

COMMIT;
""" % environ.get("BOT_TOKEN")

# Default bot prefix
create_vl = create_vl % environ.get("BOT_PREFIX")
