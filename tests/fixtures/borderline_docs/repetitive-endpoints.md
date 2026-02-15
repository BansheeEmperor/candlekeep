---
title: "Endpoint Reference"
description: "API endpoint reference documentation"
keywords: ["API", "endpoints", "reference"]
category: "design"
tags: ["api", "reference"]
---

# Endpoint Reference

## GET /users

This endpoint returns a list of users. The endpoint accepts query parameters for filtering. The endpoint returns JSON. The endpoint requires authentication. The response includes pagination metadata. Use page and limit parameters for pagination. Results are sorted by creation date by default.

## POST /users

This endpoint creates a new user. The endpoint accepts a JSON body. The endpoint returns the created resource. The endpoint requires authentication. The response includes the new resource ID. Required fields are name and email. Optional fields include role and department.

## PUT /users/:id

This endpoint updates an existing user. The endpoint accepts a JSON body. The endpoint returns the updated resource. The endpoint requires authentication. The response includes the modified fields. All fields in the body are optional. Only provided fields are updated.

## DELETE /users/:id

This endpoint deletes a user. The endpoint requires authentication. The endpoint returns a 204 status code on success. The endpoint returns 404 if the user does not exist. Deletion is permanent and cannot be undone. Related resources are not automatically deleted.

## GET /orders

This endpoint returns a list of orders. The endpoint accepts query parameters for filtering. The endpoint returns JSON. The endpoint requires authentication. The response includes pagination metadata. Use page and limit parameters for pagination. Results are sorted by creation date by default.

## POST /orders

This endpoint creates a new order. The endpoint accepts a JSON body. The endpoint returns the created resource. The endpoint requires authentication. The response includes the new resource ID. Required fields are product_id and quantity. Optional fields include notes and priority.

## PUT /orders/:id

This endpoint updates an existing order. The endpoint accepts a JSON body. The endpoint returns the updated resource. The endpoint requires authentication. The response includes the modified fields. All fields in the body are optional. Only provided fields are updated.

## DELETE /orders/:id

This endpoint deletes an order. The endpoint requires authentication. The endpoint returns a 204 status code on success. The endpoint returns 404 if the order does not exist. Deletion is permanent and cannot be undone. Related resources are not automatically deleted.

## GET /products

This endpoint returns a list of products. The endpoint accepts query parameters for filtering. The endpoint returns JSON. The endpoint requires authentication. The response includes pagination metadata. Use page and limit parameters for pagination. Results are sorted by creation date by default.

## POST /products

This endpoint creates a new product. The endpoint accepts a JSON body. The endpoint returns the created resource. The endpoint requires authentication. The response includes the new resource ID. Required fields are name and price. Optional fields include description and category.

## PUT /products/:id

This endpoint updates an existing product. The endpoint accepts a JSON body. The endpoint returns the updated resource. The endpoint requires authentication. The response includes the modified fields. All fields in the body are optional. Only provided fields are updated.

## DELETE /products/:id

This endpoint deletes a product. The endpoint requires authentication. The endpoint returns a 204 status code on success. The endpoint returns 404 if the product does not exist. Deletion is permanent and cannot be undone. Related resources are not automatically deleted.
