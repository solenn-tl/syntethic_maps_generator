-- Create the database named "cadastre"
CREATE DATABASE cadastre;

-- Connect to the "cadastre" database
\c cadastre

-- Enable the PostGIS extension
CREATE EXTENSION postgis;

-- Create the schema named "temporary"
CREATE SCHEMA temporary;

-- Create a table to store styles in the "public" schema
CREATE TABLE styles (idstyle character varying (20), description_fr character varying (150), description_en character varying (150));
