# Form: Item Master (Add Item) — field-level parity

**Source:** https://erp.sbacindia.in/Master/ItemMasterConfig.aspx  
**Tabs:** Add Item | View Item  
**Kanha UI:** `#/inventory` → + Item  
**Status:** ✅ Complete — live page + section expand verified 2026-08-02 (all section checkboxes open)

## Locked
- Fresh entry only — no SBAC catalog import  
- Same fields + same working (Branch multi, Conversion/Vendor/Packing Add, Rate List, Stock)  
- Kanha design  
- Extras separate (`Sale Price (Kanha)` when MRP alone is set)

## Primary
| Field | Control | Notes |
|-------|---------|-------|
| Branch Name | `ddlBranchName` | |
| Item Code * | `PartNoTextBox` | auto if blank |
| Item Name * | `PartNAmeTextBox` | required |
| Part Image | `FileUpload1` | Kanha: URL for now |
| Select Brand | `ddlbrand` | + add/refresh on SBAC |
| Base Unit * | `unitDropDownList` | |
| Main Group * | `classificationDropDownList` | |
| Sub Group | `subDropDownList` | |
| Category/Make | `categoryDropDownList` | |
| HSN Code | `txthsn` | |
| Item Description | `txtitemdesc` | |
| Purchase Default Unit | `ddlPurDefUnit` | |
| Sale Default Unit | `ddlSaleDefUnit` | |
| Color | `ddlcolor` | |
| Size | `ddlsize` | |
| Branch list | multi-checkbox | same branches as Party |

## Section checkboxes
| Section | Checkbox |
|---------|----------|
| Other Section | `chkotherdiv` |
| Conversion Factor | `chkConversion` |
| Item Specification | `chkbox` |
| Item Classification | `chkitemclass` |
| Tax Duty Details | `chktaxduty` |
| Dimension | `chkdimension` |
| Stock Value | `chkstokevalue` |
| Rate List | `chkratelist` |
| Country List | `chkcountrylist` |
| Vendor Details | `chkvendorlist` |
| Packing Instruction | `PackingInstruction` |
| Sub Item | `chkSubItem` |

## Other Section
Same as Item Name · Parent Item Code · Gross / Net / Cartoon Weight · Standard Packaging Quantity · Sub Item · Subitem Required* · Area calculationrequired · Formula Reqd* · Formula

## Conversion Factor — multi via Add
Base Unit · Conversion Unit · Value · Add

## Item Specification
Item Specification (textarea)

## Item Classification
Rack No · Bin No · Purchase Name · Purchase Code · Bar Code · Finished Goods / Raw Material / Semi finished / Powder coated

## Tax Duty Details
Tarrif Classification · Duty · Commodity Code

## Dimension
Length · Width · Height · Weight · Dimension Unit · Volumetric Weight

## Stock Value
Unit · Closing Stock · Opening Stock · Monthly Consumption · Re order level · Minimum Stock · Maximum Stock · Minimum Order Quantity

## Rate List
Purchase · MRP · GST(%) · GST Include · Date · Exporter GST(%) · Exporter GST Include · Bom Rate · Active / NonActive

## Country List
Multi-country checkboxes (Kanha: common export set + Other countries text)

## Vendor Details — multi via Add
Vendor Name · Contact No. · Add

## Packing Instruction — multi via Add
Packing Unit · Serial No · Qty · Qty/Weight/Height/Width/Length units · From Unit · Add

## Actions
Submit (`SubmitButton`)

## Kanha APIs
- `POST /api/inventory/products` · `GET /api/inventory/products`
- Storage: columns + `custom` JSON (`other`, `conversions[]`, `classification`, `tax_duty`, `dimension`, `stock`, `rate_list`, `country_list`, `vendors[]`, `packings[]`)

## Full control dump
See `item-master.json` (~341 controls including nav chrome).

## Next
Sales Order deep fields — live expand + one-pass implement
