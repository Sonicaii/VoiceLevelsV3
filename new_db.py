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

CREATE TABLE sudo (
  id char(19) NOT NULL,
  PRIMARY KEY (id)
);

COMMIT;
""".format(f"\n".join(f"('{i:02d}', '{{}}')," for i in range(100)).rstrip(","))

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
('{}');

COMMIT;
""".format(

  "YOUR_BOT_TOKEN"

)
