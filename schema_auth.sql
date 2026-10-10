--
-- PostgreSQL database dump
--

\restrict SWKxRXI8vXxXK0Hniqhxe129TIBbiVWfOFsidC1NTCINX4iEXecJEIVLTg7aWMh

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

--
-- Name: role; Type: TYPE; Schema: public; Owner: secureops_admin
--

CREATE TYPE public.role AS ENUM (
    'OWNER',
    'ADMIN',
    'MEMBER',
    'VIEWER'
);


ALTER TYPE public.role OWNER TO secureops_admin;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: organizations; Type: TABLE; Schema: public; Owner: secureops_admin
--

CREATE TABLE public.organizations (
    id integer NOT NULL,
    name character varying NOT NULL,
    plan character varying,
    created_at timestamp without time zone
);


ALTER TABLE public.organizations OWNER TO secureops_admin;

--
-- Name: organizations_id_seq; Type: SEQUENCE; Schema: public; Owner: secureops_admin
--

CREATE SEQUENCE public.organizations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.organizations_id_seq OWNER TO secureops_admin;

--
-- Name: organizations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: secureops_admin
--

ALTER SEQUENCE public.organizations_id_seq OWNED BY public.organizations.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: secureops_admin
--

CREATE TABLE public.users (
    id integer NOT NULL,
    org_id integer NOT NULL,
    email character varying NOT NULL,
    password_hash character varying NOT NULL,
    role public.role NOT NULL,
    created_at timestamp without time zone
);


ALTER TABLE public.users OWNER TO secureops_admin;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: secureops_admin
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO secureops_admin;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: secureops_admin
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: organizations id; Type: DEFAULT; Schema: public; Owner: secureops_admin
--

ALTER TABLE ONLY public.organizations ALTER COLUMN id SET DEFAULT nextval('public.organizations_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: secureops_admin
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: organizations organizations_pkey; Type: CONSTRAINT; Schema: public; Owner: secureops_admin
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: secureops_admin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: secureops_admin
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: users users_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: secureops_admin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organizations(id);


--
-- PostgreSQL database dump complete
--

\unrestrict SWKxRXI8vXxXK0Hniqhxe129TIBbiVWfOFsidC1NTCINX4iEXecJEIVLTg7aWMh

