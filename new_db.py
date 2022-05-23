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
  json_contents jsonb NOT NULL DEFAULT '{{}}'
);

--
-- Dumping data for table levels
--

INSERT INTO levels (right_two, json_contents) VALUES
{};

--
-- Indexes for table levels
--
ALTER TABLE levels
  ADD PRIMARY KEY (right_two);

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
  token text NOT NULL
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
