# NYC TLC green taxi records

Publisher: New York City Taxi and Limousine Commission. This is the January 2023
green trip file and the TLC taxi-zone lookup, retained without modification.

`lpep_pickup_datetime` and `lpep_dropoff_datetime` are recorded trip timestamps.
`trip_distance` is recorded distance in miles. `PULocationID` and `DOLocationID`
refer to `LocationID` in the zone lookup. The lookup describes borough, zone and
service zone. Recorded fare/payment amounts are in US dollars. `total_amount`
is the total charged as reported; it does not capture cash tips. `tip_amount`
captures credit-card tips. Payment types are 1 credit card, 2 cash, 3 no charge,
4 dispute, 5 unknown, and 6 voided trip in the published dictionary.

The source publisher does not warrant submitted trip completeness or accuracy.
The current published dictionary describes newer schema fields as well; inspect
the supplied file for the actual columns. This note supplies no measured quality
counts, task answers, filtering recipe or reference calculations.

Source: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page
Dictionary: https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_green.pdf
Use terms: https://www.nyc.gov/opendata/get-started/FAQs and https://www.nyc.gov/main/terms-of-use
Source documentation consulted during qualification on 2026-11-13.
