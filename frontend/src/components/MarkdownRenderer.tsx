"use client";

import React from 'react';
import DOMPurify from 'dompurify';

interface MarkdownRendererProps {
    content: string;
    className?: string;
}

/**
 * Secure Markdown Renderer using DOMPurify for XSS protection.
 * 
 * Supports:
 * - Headers (# ## ###)
 * - Bullet points (-)
 * - Numbered lists (1. 2. 3.)
 * - Bold text (**text**)
 * - Paragraphs
 */
export default function MarkdownRenderer({ content, className = '' }: MarkdownRendererProps) {
    if (!content) return null;

    // Configure DOMPurify to only allow safe tags
    const purifyConfig = {
        ALLOWED_TAGS: ['strong', 'em', 'b', 'i', 'br'],
        ALLOWED_ATTR: [],
    };

    /**
     * Parse markdown text and convert to safe HTML.
     * Uses DOMPurify to sanitize all output.
     */
    const parseMarkdown = (text: string): string => {
        if (!text) return '';
        
        // Convert markdown bold **text** to <strong>text</strong>
        let html = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Convert markdown italic *text* to <em>text</em> (but not if it's bold)
        html = html.replace(/(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)/g, '<em>$1</em>');
        
        // Sanitize the result
        return DOMPurify.sanitize(html, purifyConfig);
    };

    // Split content into lines for processing
    const lines = content.split('\n');
    
    return (
        <div className={`space-y-4 text-gray-800 ${className}`}>
            {lines.map((line, index) => {
                const trimmedLine = line.trim();
                
                // Skip empty lines
                if (trimmedLine === '') {
                    return <div key={index} className="h-2" />;
                }
                
                // Header 1: # Title
                if (trimmedLine.startsWith('# ')) {
                    const text = trimmedLine.slice(2);
                    return (
                        <h3 
                            key={index} 
                            className="text-xl font-bold mt-6 mb-3 text-gray-900"
                            dangerouslySetInnerHTML={{ __html: parseMarkdown(text) }}
                        />
                    );
                }
                
                // Header 2: ## Title
                if (trimmedLine.startsWith('## ')) {
                    const text = trimmedLine.slice(3);
                    return (
                        <h4 
                            key={index} 
                            className="text-lg font-semibold mt-5 mb-2 text-gray-800"
                            dangerouslySetInnerHTML={{ __html: parseMarkdown(text) }}
                        />
                    );
                }
                
                // Header 3: ### Title
                if (trimmedLine.startsWith('### ')) {
                    const text = trimmedLine.slice(4);
                    return (
                        <h5 
                            key={index} 
                            className="text-base font-semibold mt-4 mb-2 text-gray-800"
                            dangerouslySetInnerHTML={{ __html: parseMarkdown(text) }}
                        />
                    );
                }
                
                // Bullet point: - Item
                if (trimmedLine.startsWith('- ')) {
                    const text = trimmedLine.slice(2);
                    return (
                        <div key={index} className="flex flex-row items-start ml-2 mb-1">
                            <span className="mr-2 text-gray-400">•</span>
                            <span dangerouslySetInnerHTML={{ __html: parseMarkdown(text) }} />
                        </div>
                    );
                }
                
                // Numbered list: 1. Item
                const numberedMatch = trimmedLine.match(/^(\d+)\.\s(.+)$/);
                if (numberedMatch) {
                    const [, number, text] = numberedMatch;
                    return (
                        <div key={index} className="flex flex-row items-start ml-2 mb-1">
                            <span className="mr-2 text-gray-500 font-medium">{number}.</span>
                            <span dangerouslySetInnerHTML={{ __html: parseMarkdown(text) }} />
                        </div>
                    );
                }
                
                // Regular paragraph
                return (
                    <p 
                        key={index} 
                        className="leading-relaxed"
                        dangerouslySetInnerHTML={{ __html: parseMarkdown(line) }}
                    />
                );
            })}
        </div>
    );
}
