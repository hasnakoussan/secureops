--
-- PostgreSQL database dump
--

\restrict 5f6DdhJUOpzNInMFbe69QZE9BiaXah3PQcCopo0I8o9iwJEAbShWU66PQ53izXP

-- Dumped from database version 16.13
-- Dumped by pg_dump version 16.15

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: findings; Type: TABLE; Schema: public; Owner: secureops_admin
--

CREATE TABLE public.findings (
    id integer NOT NULL,
    scan_id integer NOT NULL,
    source character varying NOT NULL,
    rule_id character varying NOT NULL,
    file_path character varying NOT NULL,
    line integer NOT NULL,
    severity character varying,
    message text
);


ALTER TABLE public.findings OWNER TO secureops_admin;

--
-- Name: findings_id_seq; Type: SEQUENCE; Schema: public; Owner: secureops_admin
--

CREATE SEQUENCE public.findings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.findings_id_seq OWNER TO secureops_admin;

--
-- Name: findings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: secureops_admin
--

ALTER SEQUENCE public.findings_id_seq OWNED BY public.findings.id;


--
-- Name: scans; Type: TABLE; Schema: public; Owner: secureops_admin
--

CREATE TABLE public.scans (
    id integer NOT NULL,
    org_id integer NOT NULL,
    repo_url character varying NOT NULL,
    score integer,
    classification character varying,
    critical_count integer,
    high_count integer,
    medium_count integer,
    secrets_count integer,
    status character varying,
    failed_scanners text,
    error_message text,
    started_at timestamp without time zone,
    finished_at timestamp without time zone
);


ALTER TABLE public.scans OWNER TO secureops_admin;

--
-- Name: scans_id_seq; Type: SEQUENCE; Schema: public; Owner: secureops_admin
--

CREATE SEQUENCE public.scans_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.scans_id_seq OWNER TO secureops_admin;

--
-- Name: scans_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: secureops_admin
--

ALTER SEQUENCE public.scans_id_seq OWNED BY public.scans.id;


--
-- Name: findings id; Type: DEFAULT; Schema: public; Owner: secureops_admin
--

ALTER TABLE ONLY public.findings ALTER COLUMN id SET DEFAULT nextval('public.findings_id_seq'::regclass);


--
-- Name: scans id; Type: DEFAULT; Schema: public; Owner: secureops_admin
--

ALTER TABLE ONLY public.scans ALTER COLUMN id SET DEFAULT nextval('public.scans_id_seq'::regclass);


--
-- Name: findings findings_pkey; Type: CONSTRAINT; Schema: public; Owner: secureops_admin
--

ALTER TABLE ONLY public.findings
    ADD CONSTRAINT findings_pkey PRIMARY KEY (id);


--
-- Name: scans scans_pkey; Type: CONSTRAINT; Schema: public; Owner: secureops_admin
--

ALTER TABLE ONLY public.scans
    ADD CONSTRAINT scans_pkey PRIMARY KEY (id);


--
-- Name: findings findings_scan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: secureops_admin
--

ALTER TABLE ONLY public.findings
    ADD CONSTRAINT findings_scan_id_fkey FOREIGN KEY (scan_id) REFERENCES public.scans(id);


--
-- PostgreSQL database dump complete
--

\unrestrict 5f6DdhJUOpzNInMFbe69QZE9BiaXah3PQcCopo0I8o9iwJEAbShWU66PQ53izXP

